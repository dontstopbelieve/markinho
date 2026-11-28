# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 dontstopbelieve — Markinho
"""Pacotes extras: gerar, conferir, instalar, juntar com os modelos embutidos e recusar pacotes adulterados."""
import json
import zipfile
from pathlib import Path

import pytest

from markinho import packs
from markinho.packs import MANIFEST, PACKS_BY_ID, PackError, build_pack, install_from_zip

FOLDER = "docling-project--CodeFormulaV2"


@pytest.fixture
def env(tmp_path, monkeypatch):
    """Modelos embutidos (layout/tabelas) numa pasta e a pasta do usuário noutra."""
    bundled = tmp_path / "programa" / "models"
    (bundled / "docling" / "docling-project--docling-layout-heron").mkdir(parents=True)
    (bundled / "docling" / "docling-project--docling-layout-heron" / "model.bin").write_bytes(b"layout")
    monkeypatch.setenv("MARKINHO_MODELS", str(bundled))
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "usuario"))
    monkeypatch.setattr(packs, "docling_available", lambda: True)
    monkeypatch.setattr(packs, "tesseract_available", lambda: True)
    src = tmp_path / "fonte"
    (src / "docling" / FOLDER / "sub").mkdir(parents=True)
    (src / "docling" / FOLDER / "model.safetensors").write_bytes(b"x" * 5000)
    (src / "docling" / FOLDER / "sub" / "config.json").write_text("{}")
    for d in ("tessdata", "tessdata_best"):
        (src / d).mkdir()
        for lang in packs.OCR_LANGS:
            (src / d / f"{lang}.traineddata").write_bytes(lang.encode() * 10)
    return tmp_path, src


def _pack(env_):
    tmp, src = env_
    return build_pack(PACKS_BY_ID["formulas"], src, tmp / "rel", "9.9.9")


def test_gera_e_instala(env):
    pk = PACKS_BY_ID["formulas"]
    z = _pack(env)
    assert z.name == "Markinho-Pacote-Formulas-9.9.9.zip"
    assert pk.url("9.9.9").endswith("/download/pacotes-9.9.9/Markinho-Pacote-Formulas-9.9.9.zip")
    assert pk.url() == f"{packs.RELEASES}/download/{packs.PACKS_TAG}/{pk.file_name()}"
    assert not packs.installed(pk)
    seen = []
    assert install_from_zip(z, lambda d, t: seen.append((d, t)), check_version="9.9.9") is pk
    assert packs.installed(pk) and seen[-1][0] == seen[-1][1] == 5002
    user = packs.user_docling_dir()
    assert (user / FOLDER / "model.safetensors").read_bytes() == b"x" * 5000
    assert not any(p.name.startswith(".instalando") for p in user.iterdir())
    # o Docling enxerga tudo numa pasta só: o pacote e os modelos embutidos
    merged = packs.merged_docling_dir()
    assert merged == user
    assert (merged / "docling-project--docling-layout-heron" / "model.bin").read_bytes() == b"layout"
    from markinho.models import docling_artifacts

    assert docling_artifacts() == user
    # reinstalar por cima e remover
    install_from_zip(z)
    assert packs.uninstall(pk) and not packs.installed(pk)
    assert (packs._bundled() / "docling-project--docling-layout-heron").is_dir()     # embutido intacto


def test_sempre_igual(env):
    tmp, src = env
    a = build_pack(PACKS_BY_ID["formulas"], src, tmp / "a", "1").read_bytes()
    b = build_pack(PACKS_BY_ID["formulas"], src, tmp / "b", "1").read_bytes()
    assert a == b                   # o SHA-256 do instalador bate com o da página de versões


def test_sem_pacote_usa_so_os_embutidos(env):
    assert packs.merged_docling_dir() == packs._bundled()


def test_atalho_quebrado_e_refeito(env, tmp_path):
    install_from_zip(_pack(env))
    user = packs.user_docling_dir()
    link = user / "docling-project--docling-layout-heron"
    packs.merged_docling_dir()
    assert packs._is_link(link)
    link.unlink()
    link.symlink_to(tmp_path / "nao-existe", target_is_directory=True)
    packs.merged_docling_dir()
    assert (link / "model.bin").is_file()


def _rewrite(z, tmp_path, change):
    """Copia o pacote mudando o conteúdo (simula download corrompido ou arquivo adulterado)."""
    out = tmp_path / "ruim.zip"
    with zipfile.ZipFile(z) as src, zipfile.ZipFile(out, "w") as dst:
        items = {i.filename: src.read(i.filename) for i in src.infolist()}
        change(items)
        for name, data in items.items():
            dst.writestr(name, data)
    return out


def _manifest(items):
    return json.loads(items[MANIFEST])


@pytest.mark.parametrize("caso", ["corrompido", "extra", "faltando", "fuga", "formato", "desconhecido",
                                  "nao_pacote", "maior"])
def test_recusa_pacote_ruim(env, tmp_path, caso):
    z = _pack(env)
    name = f"docling/{FOLDER}/model.safetensors"

    def change(items):
        m = _manifest(items)
        if caso == "corrompido":
            items[name] = b"y" * 5000
        elif caso == "extra":
            items["docling/outro/virus.exe"] = b"MZ"
        elif caso == "faltando":
            del items[name]
        elif caso == "fuga":
            m["arquivos"]["docling/../../fora.txt"] = {"sha256": "0" * 64, "tamanho": 1}
            items["docling/../../fora.txt"] = b"!"
        elif caso == "formato":
            m["formato"] = 99
        elif caso == "desconhecido":
            m["pacote"] = "bitcoin"
        elif caso == "nao_pacote":
            del items[MANIFEST]
            return
        elif caso == "maior":
            items[name] = b"x" * 6000
        items[MANIFEST] = json.dumps(m).encode()

    bad = _rewrite(z, tmp_path, change)
    with pytest.raises(PackError):
        install_from_zip(bad)
    assert not packs.installed(PACKS_BY_ID["formulas"])
    assert not (tmp_path / "fora.txt").exists()


def test_recusa_outra_versao_arquivo_invalido_e_edicao(env, tmp_path, monkeypatch):
    z = _pack(env)
    with pytest.raises(PackError):
        install_from_zip(z, check_version="1.0.0")
    (tmp_path / "x.zip").write_bytes(b"isto nao e zip")
    with pytest.raises(PackError):
        install_from_zip(tmp_path / "x.zip")
    monkeypatch.setattr(packs, "docling_available", lambda: False)
    with pytest.raises(PackError, match="COMPLETA"):
        install_from_zip(z)
    monkeypatch.setattr(packs, "tesseract_available", lambda: False)
    with pytest.raises(PackError, match="Tesseract"):
        install_from_zip(build_pack(PACKS_BY_ID["idiomas"], env[1], tmp_path / "i", "9.9.9"))


def test_build_sem_modelo(env, tmp_path):
    with pytest.raises(PackError):
        build_pack(PACKS_BY_ID["formulas"], tmp_path / "vazio", tmp_path / "o", "1")
    with pytest.raises(PackError):
        build_pack(PACKS_BY_ID["idiomas"], tmp_path / "vazio", tmp_path / "o", "1")


def test_textos_explicam_para_quem_serve():
    for pk in packs.PACKS:
        assert pk.name and pk.what and "Vale a pena" in pk.who and "Dispensável" in pk.skip


def test_terminal(env, capsys):
    from markinho.__main__ import cli

    z = _pack(env)
    assert cli(["--pacotes"]) == 0
    assert "Não instalado" in capsys.readouterr().out
    assert cli(["--instalar-pacote", str(z)]) == 0
    assert cli(["--instalar-pacote", str(z.with_name("nao.zip"))]) == 1
    cli(["--pacotes"])
    assert ": Instalado" in capsys.readouterr().out


def test_janela(env, monkeypatch):
    from PySide6.QtWidgets import QMessageBox

    from markinho.gui_tools import PacksDialog

    monkeypatch.setattr(QMessageBox, "information", lambda *a, **k: None)
    monkeypatch.setattr(QMessageBox, "warning", lambda *a, **k: None)
    monkeypatch.setattr(QMessageBox, "question", lambda *a, **k: QMessageBox.Yes)
    opened = []
    monkeypatch.setattr("PySide6.QtGui.QDesktopServices.openUrl", lambda u: opened.append(u.toString()))
    z = _pack(env)
    d = PacksDialog(None)
    pk = PACKS_BY_ID["formulas"]
    assert "Não instalado" in d.status["formulas"].text() and "idiomas" in d.status
    assert not d.install(pk, str(z.with_name("nao.zip")))
    assert d.install(pk, str(z))
    assert "Instalado" in d.status["formulas"].text() and d.remove_btn["formulas"].isEnabled()
    d.open_page(pk)
    assert opened == [packs.PACKS_PAGE] and "/releases/tag/pacotes-" in opened[0]
    d.remove(pk)
    assert "Não instalado" in d.status["formulas"].text()
    d.deleteLater()


# ---------------------------------------------------------------- idiomas extras do OCR
def test_idiomas_juntam_com_os_do_tesseract(env, tmp_path, monkeypatch):
    from markinho import ocr

    base = tmp_path / "sistema" / "tessdata"
    (base / "configs").mkdir(parents=True)
    (base / "configs" / "tsv").write_text("tessedit_create_tsv 1")
    for lang in ("por", "eng", "osd"):
        (base / f"{lang}.traineddata").write_bytes(b"base")
    monkeypatch.setattr(ocr, "base_languages", lambda: {"por", "eng"})
    monkeypatch.setattr(ocr, "bundled_best_dir", lambda: None)
    pk = PACKS_BY_ID["idiomas"]
    assert packs.merged_tessdata(base) is None              # sem pacote: fica a pasta do sistema
    assert not packs.installed(pk) and not packs.removable(pk)
    install_from_zip(build_pack(pk, env[1], tmp_path / "rel", "9.9.9"))
    assert packs.installed(pk) and packs.removable(pk)
    merged = packs.merged_tessdata(base)
    names = {f.name for f in merged.iterdir()}
    assert {"por.traineddata", "spa.traineddata", "ara.traineddata", "chi_sim.traineddata", "configs"} <= names
    assert (merged / "configs" / "tsv").read_text() == "tessedit_create_tsv 1"
    assert (merged / "por.traineddata").read_bytes() == b"base"
    best = packs.merged_tessdata(None, "tessdata_best")
    assert (best / "rus.traineddata").is_file()
    packs.uninstall(pk)
    assert not packs.installed(pk)
    assert (base / "por.traineddata").is_file()             # o do sistema nunca é apagado


def test_ocr_usa_pasta_juntada(env, tmp_path, monkeypatch):
    from markinho import ocr

    if ocr.tesseract_cmd() is None:
        pytest.skip("sem Tesseract")
    install_from_zip(build_pack(PACKS_BY_ID["idiomas"], env[1], tmp_path / "rel", "9.9.9"))
    try:
        ocr.refresh()
        import os

        assert ocr.tesseract_cmd()
        assert os.environ["TESSDATA_PREFIX"] == str(packs.models_root() / "tessdata")
        assert "spa" in {f.stem for f in Path(os.environ["TESSDATA_PREFIX"]).glob("*.traineddata")}
        assert ocr.tessdata_best_dir() == str(packs.models_root() / "tessdata_best")
        assert "por" in ocr.base_languages()
    finally:
        packs.uninstall(PACKS_BY_ID["idiomas"])
        ocr.refresh()
        ocr.tesseract_cmd()


def test_chines_sem_espacos():
    from markinho.ocr import cjk_join

    assert cjk_join("本 合同 由 双方 签订 。") == "本合同由双方签订。"
    assert cjk_join("Total: 100 元 por mês") == "Total: 100 元 por mês"
    assert cjk_join("Contrato em português") == "Contrato em português"


def test_textos_explicam_cada_pacote():
    for pk in packs.PACKS:
        assert pk.need and pk.size_mb > 0 and pk.editions
    assert "espanhol" in PACKS_BY_ID["idiomas"].what and "por+spa" in PACKS_BY_ID["idiomas"].what


def test_pacote_ignora_rascunhos_do_download(env):
    tmp, src = env
    cache = src / "docling" / FOLDER / ".cache" / "huggingface"
    cache.mkdir(parents=True)
    (cache / "arvore.json").write_text("{}")
    z = build_pack(PACKS_BY_ID["formulas"], src, tmp / "limpo", "1")
    import zipfile as _z

    assert not any(".cache" in n for n in _z.ZipFile(z).namelist())
