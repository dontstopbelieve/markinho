"""Linha de comando (markinho arquivo.pdf …): os caminhos que o usuário usa no terminal."""
import json
import shutil
from pathlib import Path

import pytest

from markinho.__main__ import cli

EX = Path(__file__).resolve().parent.parent / "exemplos"


@pytest.fixture
def doc(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    src = tmp_path / "relatorio.docx"
    shutil.copy(EX / "relatorio.docx", src)
    return src


def test_cli_prints_markdown_without_output(doc, capsys):
    assert cli([str(doc), "--report"]) == 0
    assert capsys.readouterr().out.lstrip().startswith("#")


def test_cli_output_file_and_profile(doc):
    out = doc.parent / "saida" / "r.md"
    assert cli([str(doc), "-o", str(out), "--profile", "llm", "--no-fix"]) == 0
    assert out.is_file() and "![" not in out.read_text(encoding="utf-8")


def test_cli_anonymize_with_list(doc, capsys):
    lista = doc.parent / "nomes.txt"
    lista.write_text("Relatório\n", encoding="utf-8")
    out = doc.parent / "anon.md"
    assert cli([str(doc), "-o", str(out), "--anonimizar-lista", str(lista)]) == 0
    assert "relatório" not in out.read_text(encoding="utf-8").lower()
    assert "não se responsabiliza" in capsys.readouterr().err


def test_cli_chunks_and_export(doc):
    assert cli([str(doc), "--chunks", "json", "--chunk-size", "500", "-o", str(doc.parent / "p.json")]) == 0
    data = json.loads((doc.parent / "p.json").read_text(encoding="utf-8"))
    assert data["chunks"] and all(c["chars"] <= 600 for c in data["chunks"])
    assert cli([str(doc), "-t", "html", "-o", str(doc.parent / "r.html")]) == 0
    assert "<html" in (doc.parent / "r.html").read_text(encoding="utf-8").lower()


def test_cli_naming_and_existing_files(doc):
    out = doc.parent / "saida"
    args = [str(doc), "-o", str(out) + "/", "--nome", "{n}_{nome}", "--nome-seguro"]
    assert cli(args) == 0
    assert cli(args) == 0                                           # já existe: cria com sufixo
    names = sorted(p.name for p in out.glob("*.md"))
    assert len(names) == 2 and all(n.startswith("001_relatorio") for n in names)
    assert cli(args + ["--se-existir", "skip"]) == 0
    assert len(list(out.glob("*.md"))) == 2


def test_cli_info_commands(capsys):
    assert cli(["--version"]) == 0
    assert cli(["--engines"]) == 0
    out = capsys.readouterr().out
    assert "native" in out.lower() or "nativo" in out.lower()
    assert cli(["--mcp-config", "vscode"]) == 0
    assert "servers" in capsys.readouterr().out


def test_cli_missing_file_fails(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    assert cli([str(tmp_path / "nao_existe.pdf")]) != 0
