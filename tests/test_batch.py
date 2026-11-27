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


def test_retomar_pula_o_que_ja_esta_pronto(lote, capsys):
    src, out = lote
    assert _run(src, out) == 0
    reg = json.loads((out / batch.MANIFEST).read_text(encoding="utf-8"))["files"]
    assert len(reg) == 3 and all(e["status"] == "ok" and len(e["sha256"]) == 64 for e in reg.values())
    capsys.readouterr()
    assert _run(src, out) == 0
    err = capsys.readouterr().err
    assert err.count("sem mudanças — pulado") == 3 and "0 convertido(s), 3 pulado(s)" in err
    assert sorted(p.name for p in out.glob("*.md")) == ["doc0.md", "doc1.md", "doc2.md"]   # nada de doc0_2.md


def test_retomar_refaz_o_que_mudou_ou_faltou(lote, capsys):
    src, out = lote
    assert _run(src, out) == 0
    (out / "doc1.md").unlink()                                   # saída apagada
    with open(src / "doc2.docx", "ab") as f:                     # arquivo de origem mudou
        f.write(b"\0")
    capsys.readouterr()
    assert _run(src, out) == 0
    err = capsys.readouterr().err
    assert "2 convertido(s), 1 pulado(s)" in err
    assert (out / "doc1.md").is_file() and not (out / "doc2_2.md").exists()
    capsys.readouterr()
    assert _run(src, out, "--profile", "llm") == 0              # configuração mudou: refaz tudo
    assert "3 convertido(s)" in capsys.readouterr().err


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
    monkeypatch.setattr(m, "convert", real)
    capsys.readouterr()
    assert _run(src, out) == 0
    assert "2 convertido(s), 1 pulado(s)" in capsys.readouterr().err
    assert not list(out.glob(".~*"))                            # nenhum temporário largado


def test_erro_fica_registrado_e_e_refeito(lote, capsys):
    src, out = lote
    (src / "quebrado.pdf").write_bytes(b"%PDF-1.4 isto nao e um pdf")
    assert _run(src, out, "-e", "native") == 1
    reg = json.loads((out / batch.MANIFEST).read_text(encoding="utf-8"))["files"]
    assert any(e["status"] == "erro" for e in reg.values())
    texto = (out / batch.MANIFEST).read_text(encoding="utf-8")
    assert "quebrado" not in texto and "entrada" not in texto and "doc0.docx" not in texto   # sem nomes de origem
    capsys.readouterr()
    _run(src, out, "-e", "native")
    err = capsys.readouterr().err
    assert "0 convertido(s), 3 pulado(s)" in err and "1 com erro" in err   # tenta de novo o que falhou


def test_registro_mexido_nao_grava_fora_da_pasta(lote, tmp_path):
    src, out = lote
    assert _run(src, out) == 0
    path = out / batch.MANIFEST
    data = json.loads(path.read_text(encoding="utf-8"))
    for e in data["files"].values():
        e["output"] = "../fora.md"
        e["status"] = "convertendo"
    path.write_text(json.dumps(data), encoding="utf-8")
    assert _run(src, out) == 0
    assert not (tmp_path / "fora.md").exists()
    path.write_text("{ estragado", encoding="utf-8")                # registro estragado: recomeça sem quebrar
    assert _run(src, out) == 0


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
    capsys.readouterr()
    assert _run(src, out, "-t", "html") == 0
    assert "3 pulado(s)" in capsys.readouterr().err
