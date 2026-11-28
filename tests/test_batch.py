"""Lotes que retomam de onde pararam (--retomar): impressão digital por arquivo, nada é refeito à toa."""
import json
import shutil
from pathlib import Path

import pytest

from markinho import batch
from markinho.__main__ import cli

EX = Path(__file__).resolve().parent.parent / "exemplos"


@pytest.fixture
def lote(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    src = tmp_path / "entrada"
    src.mkdir()
    for i in range(3):
        shutil.copy(EX / "relatorio.docx", src / f"doc{i}.docx")
    return src, tmp_path / "saida"


def _run(src, out, *extra):
    return cli([*sorted(str(p) for p in src.iterdir()), "-o", str(out) + "/", "--retomar", *extra])


def _registro(out):
    return batch.Manifest(out).path


def test_lote_completo_apaga_o_registro(lote, capsys):
    src, out = lote
    assert _run(src, out) == 0
    assert sorted(p.name for p in out.iterdir()) == ["doc0.md", "doc1.md", "doc2.md"]   # nada a mais na pasta
    assert not _registro(out).exists()                            # terminou sem erro: registro apagado
    assert "3 convertido(s), 0 pulado(s)" in capsys.readouterr().err


def test_queda_no_meio_do_lote(lote, capsys, monkeypatch):
    """Simula o computador desligando durante o 2º arquivo: ao retomar, só o que faltou é feito."""
    src, out = lote
    import markinho.core as m

    real, calls = m.convert, []

    def boom(f, *a, **k):
        calls.append(Path(f).name)
        if len(calls) == 2:
            raise KeyboardInterrupt
        return real(f, *a, **k)

    monkeypatch.setattr(m, "convert", boom)
    with pytest.raises(KeyboardInterrupt):
        _run(src, out)
    assert _registro(out).exists() and not (out / batch.MANIFEST).exists()   # guardado só na pasta interna
    monkeypatch.setattr(m, "convert", real)
    capsys.readouterr()
    assert _run(src, out) == 0
    assert "2 convertido(s), 1 pulado(s)" in capsys.readouterr().err
    assert not list(out.glob(".~*"))                            # nenhum temporário largado
    assert sorted(p.name for p in out.glob("*.md")) == ["doc0.md", "doc1.md", "doc2.md"]
    assert not _registro(out).exists()                          # retomou e terminou: apagado


def test_erro_fica_registrado_e_e_refeito(lote, capsys):
    src, out = lote
    (src / "quebrado.pdf").write_bytes(b"%PDF-1.4 isto nao e um pdf")
    assert _run(src, out, "-e", "native") == 1
    reg = json.loads(_registro(out).read_text(encoding="utf-8"))["files"]
    assert any(e["status"] == "erro" for e in reg.values())
    texto = _registro(out).read_text(encoding="utf-8")
    assert "quebrado" not in texto and "entrada" not in texto and "doc0.docx" not in texto   # sem nomes de origem
    capsys.readouterr()
    _run(src, out, "-e", "native")
    err = capsys.readouterr().err
    assert "0 convertido(s), 3 pulado(s)" in err and "1 com erro" in err   # tenta de novo o que falhou


def test_registro_mexido_nao_grava_fora_da_pasta(lote, tmp_path):
    src, out = lote
    path = _registro(out)
    path.parent.mkdir(parents=True, exist_ok=True)
    files = {batch.Manifest.key(p): {"output": "../fora.md", "status": "convertendo", "config": "x", "sha256": "0"}
             for p in src.iterdir()}
    path.write_text(json.dumps({"markinho": 1, "files": files}), encoding="utf-8")
    assert _run(src, out) == 0
    assert not (tmp_path / "fora.md").exists()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("{ estragado", encoding="utf-8")                # registro estragado: recomeça sem quebrar
    assert _run(src, out) == 0


def test_registro_antigo_na_pasta_de_saida_e_aproveitado_e_apagado(lote):
    src, out = lote
    out.mkdir()
    old = out / batch.MANIFEST
    old.write_text(json.dumps({"markinho": 1, "files": {"abc": {"status": "erro"}}}), encoding="utf-8")
    m = batch.Manifest(out)
    assert not old.exists() and "abc" in m.entries and m.path.exists()
    assert not m.close()                                           # com erro registrado, fica para retomar


def test_retomar_exige_pasta(lote):
    src, _ = lote
    with pytest.raises(SystemExit):
        cli([str(src / "doc0.docx"), "--retomar"])
    with pytest.raises(SystemExit):
        cli([str(src / "doc0.docx"), "--retomar", "--skill", "-o", "x/"])


def test_gravacao_atomica(tmp_path, monkeypatch):
    alvo = tmp_path / "a.md"
    batch.atomic_write(alvo, "primeira")
    assert alvo.read_text() == "primeira"

    def falha(*a, **k):
        raise OSError("disco cheio")

    monkeypatch.setattr(batch.os, "replace", falha)
    with pytest.raises(OSError):
        batch.atomic_write(alvo, "segunda")
    assert alvo.read_text() == "primeira" and not list(tmp_path.glob(".~*"))


def test_exportacao_com_retomar(lote, capsys):
    src, out = lote
    assert _run(src, out, "-t", "html") == 0
    assert len(list(out.glob("*.html"))) == 3 and not list(out.glob(".~*"))
    assert not _registro(out).exists() and not (out / batch.MANIFEST).exists()
