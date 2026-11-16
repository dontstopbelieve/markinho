"""Regras de negócio: correção de caracteres, pedaços para IA, exportação e anonimização.

Cada teste descreve um caso real de uso; o objetivo é garantir o comportamento, não só a cobertura.
"""
import builtins
import io
import json
from pathlib import Path

import pytest

from markinho.textfix import FixOptions, FixReport, fix_mojibake, fix_text


# --------------------------------------------------------------------------- #
# Correção de caracteres (textfix)
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("bad, good", [
    ("AÃ§Ã£o e informaÃ§Ã£o", "Ação e informação"),          # UTF-8 lido como Latin-1 (mojibake)
    ("c¸ao", "çao"),                                          # cedilha solta de PDF
    ("Ol\x93a\x94", "Ol“a”"),                                 # aspas do Windows (cp1252)
    ("pala-\nvra", "palavra"),                                # hifenização no fim da linha
    ("&amp; &eacute;", "& é"),                                # entidades HTML
    ("a​b\u0007c", "abc"),                               # invisíveis e controle
    ("café ﬁm", "café fim"),                            # acento combinado e ligadura
])
def test_textfix_common_problems(bad, good):
    out, rep = fix_text(bad)
    assert out == good and rep.total >= 1


def test_textfix_cid_glyphs_warn_and_report():
    out, rep = fix_text("(cid:12)texto (cid:7)")
    assert "(cid" not in out and rep.cid_removed == 2
    md = rep.to_markdown()
    assert "correção" in md and "⚠" in md and "OCR" in md


def test_textfix_options_can_turn_everything_off():
    text = "AÃ§Ã£o pala-\nvra &amp;"
    out, rep = fix_text(text, FixOptions.none())
    assert out == text and rep.total == 0
    assert fix_text("ok")[1].to_markdown().startswith("Nenhuma correção")
    assert set(FixOptions().to_dict()) == set(FixOptions.keys())


def test_textfix_mojibake_without_ftfy(monkeypatch):
    real_import = builtins.__import__

    def no_ftfy(name, *a, **k):
        if name == "ftfy":
            raise ImportError(name)
        return real_import(name, *a, **k)

    monkeypatch.setattr(builtins, "__import__", no_ftfy)
    rep = FixReport()
    assert fix_mojibake("AÃ§Ã£o", rep) == "Ação" and rep.total == 1
    rep = FixReport()
    assert fix_mojibake("aspas \x93ok\x94", rep) == "aspas “ok”"
    assert fix_mojibake("texto limpo", FixReport()) == "texto limpo"


# --------------------------------------------------------------------------- #
# Pedaços para IA / RAG (chunker)
# --------------------------------------------------------------------------- #
DOC = """---
title: "Manual"
---

<!-- página 1 -->
# Introdução

Primeira frase. Segunda frase do parágrafo de introdução.

## Instalação

- passo um
- passo dois
  - detalhe

| Coluna A | Coluna B |
|---|---|
""" + "\n".join(f"| linha {i} | valor {i} |" for i in range(60)) + """

```python
""" + "\n".join(f"print({i})" for i in range(80)) + """
```

<!-- página 2 -->
## Uso

![figura](manual_assets/imagem_001.png)

<table>
<tr><th>A</th></tr>
""" + "\n".join(f"<tr><td>{i}</td></tr>" for i in range(60)) + """
</table>

""" + " ".join(f"Frase número {i} com algumas palavras." for i in range(120))


def test_chunks_respect_limit_and_keep_tables_and_code_whole():
    from markinho.chunker import chunk_markdown

    chunks = chunk_markdown(DOC, max_chars=600, overlap=80, source="manual.pdf")
    assert chunks and all(c.chars <= 600 + 80 for c in chunks)
    tables = [c for c in chunks if "| linha" in c.text]
    assert len(tables) > 1 and all("| Coluna A | Coluna B |" in c.text for c in tables)   # cabeçalho repetido
    html = [c for c in chunks if "<td>" in c.text]
    assert all(c.text.count("<table") == c.text.count("</table>") for c in html)
    code = [c for c in chunks if "print(" in c.text]
    assert all(c.text.count("```") % 2 == 0 for c in code)                              # bloco nunca aberto
    assert chunks[0].id == "manual-0000" and chunks[-1].page_end == 2
    assert any("Instalação" in " ".join(c.headings) for c in chunks)


@pytest.mark.parametrize("strategy", ["title", "size", "page"])
def test_chunk_strategies(strategy):
    from markinho.chunker import chunk_markdown, to_json, to_jsonl

    chunks = chunk_markdown(DOC, max_chars=800, overlap=100, strategy=strategy, overlap_all=True)
    assert len(chunks) > 3
    lines = to_jsonl(chunks, {"source": "manual.pdf"}).strip().split("\n")
    assert len(lines) == len(chunks) and json.loads(lines[0])["document"]["source"] == "manual.pdf"
    data = json.loads(to_json(chunks, {"source": "x"}, {"strategy": strategy}))
    assert data["settings"]["strategy"] == strategy and len(data["chunks"]) == len(chunks)


def test_long_sentence_and_overlap():
    from markinho.chunker import _split_text

    text = "palavra " * 400 + ". Fim."
    parts = _split_text(text, 200, 40)
    assert all(len(p) <= 200 for p in parts) and len(parts) > 10
    assert _split_text("curto", 200, 40) == ["curto"]


# --------------------------------------------------------------------------- #
# Exportação
# --------------------------------------------------------------------------- #
MD = """# Relatório

Texto com **negrito**, *itálico*, ~~riscado~~ e `código`.

1. Primeiro
2. Segundo
   - sub item

> Citação importante.

| A | B |
|---|---|
| 1 | 2 |

```
bloco de código
```
"""


@pytest.mark.parametrize("fmt, ext", [("html", ".html"), ("plain", ".txt"), ("docx", ".docx"), ("pdf", ".pdf"),
                                      ("chunks_jsonl", ".jsonl"), ("chunks_json", ".json")])
def test_native_export(tmp_path, fmt, ext):
    from markinho.exporter import export

    target = tmp_path / ("saida" + ext)
    assert export(MD, target, fmt, {"title": "Relatório", "toc": True}, backend="native") == "native"
    assert target.is_file() and target.stat().st_size > 50
    if fmt == "plain":
        txt = target.read_text(encoding="utf-8")
        assert "Relatório" in txt and "**" not in txt and "Citação" in txt
    if fmt == "html":
        assert "<title>Relatório</title>" in target.read_text(encoding="utf-8")


def test_native_docx_has_structure_and_no_author(tmp_path):
    import docx

    from markinho.exporter import export

    target = tmp_path / "r.docx"
    export(MD, target, "docx", {"title": "Relatório"}, backend="native")
    d = docx.Document(target)
    texts = [p.text for p in d.paragraphs]
    assert "Relatório" in texts and any("Primeiro" in t for t in texts) and len(d.tables) == 1
    assert d.core_properties.author == "" and d.core_properties.title == "Relatório"


def test_export_rejects_unknown_backend(tmp_path):
    from markinho.exporter import export

    with pytest.raises(RuntimeError):
        export(MD, tmp_path / "x.html", "html", backend="inexistente")


# --------------------------------------------------------------------------- #
# Anonimização: casos extras
# --------------------------------------------------------------------------- #
def test_anonymize_more_kinds():
    from markinho.anonymize import AnonOptions, anonymize

    text = ("IP 192.168.0.10, placa ABC1D23, CNH 12345678900, CEP: 01310100, título 1023 8501 0671, "
            "PIS 120.56849.90-0, cartão 4111-1111-1111-1111, (21) 3333-4444, +55 11 98765 4321.")
    out, rep = anonymize(text, AnonOptions(kinds=["ip", "placa", "rg", "cep", "titulo", "pis", "cartao",
                                                  "telefone"], mode="marcador"))
    for secret in ("192.168", "ABC1D23", "12345678900", "01310100", "1023 8501", "120.56849", "4111", "3333",
                   "98765"):
        assert secret not in out, secret
    assert rep.total == 9


def test_anonymize_word_list_ignores_comments_and_short_terms():
    from markinho.anonymize import AnonOptions, anonymize

    out, rep = anonymize("Ana e Bia foram.", AnonOptions(kinds=[], words="# comentário\nB\nAna", mode="mascara"))
    assert out == "A. e Bia foram." and rep.counts["lista"] == 1


def test_image_metadata_webp_and_broken_files():
    from PIL import Image

    from markinho.anonymize import strip_image_metadata

    exif = Image.Exif()
    exif[0x010F] = "CameraSecreta"
    buf = io.BytesIO()
    Image.new("RGB", (8, 8), "blue").save(buf, "WEBP", exif=exif.tobytes())
    clean = strip_image_metadata(buf.getvalue())
    assert b"CameraSecreta" in buf.getvalue() and b"CameraSecreta" not in clean
    assert Image.open(io.BytesIO(clean)).size == (8, 8)
    assert strip_image_metadata(b"\xff\xd8lixo") == b"\xff\xd8lixo"       # arquivo quebrado: não altera
    assert strip_image_metadata(b"GIF89a...") == b"GIF89a..."


# --------------------------------------------------------------------------- #
# Servidor MCP: configuração
# --------------------------------------------------------------------------- #
def test_mcp_config_from_environment(tmp_path, monkeypatch):
    from markinho import mcp_server

    monkeypatch.setattr(mcp_server, "config_path", lambda: tmp_path / "mcp.json")
    (tmp_path / "mcp.json").write_text("{quebrado", encoding="utf-8")
    monkeypatch.delenv("MARKINHO_MCP_FOLDERS", raising=False)
    monkeypatch.delenv("MARKINHO_MCP_ALLOW_WRITE", raising=False)
    assert mcp_server.load_config() == {"folders": [], "allow_write": False}      # JSON quebrado: padrão seguro
    monkeypatch.setenv("MARKINHO_MCP_FOLDERS", str(tmp_path) + __import__("os").pathsep + str(tmp_path / "nao"))
    monkeypatch.setenv("MARKINHO_MCP_ALLOW_WRITE", "1")
    assert mcp_server.allowed_folders() == [tmp_path.resolve()] and mcp_server.load_config()["allow_write"]
    with pytest.raises(mcp_server.AccessDenied):
        mcp_server.check_path("a\x00b")
    with pytest.raises(mcp_server.AccessDenied):
        mcp_server.check_path("nao_existe.pdf")
    rel = tmp_path / "doc.txt"
    rel.write_text("x")
    assert mcp_server.check_path("doc.txt") == rel.resolve()               # relativo: dentro da 1ª pasta


def test_mcp_client_configs(tmp_path):
    from markinho import mcp_server

    assert "servers" in mcp_server.client_config("vscode")
    assert mcp_server.client_config()["mcpServers"]["markinho"]["args"][-1] == "--mcp"
    bad = tmp_path / "c.json"
    bad.write_text("{nao é json")
    with pytest.raises(RuntimeError):
        mcp_server.install_claude_desktop(bad)
    assert str(mcp_server.claude_desktop_config_path()).endswith("claude_desktop_config.json")


MD_RICH = MD + """
#### Subtítulo nível 4

Link para [o site](https://exemplo.com) e imagem ![logo](logo.png).<br>Quebra.

---

<div><p>Bloco HTML</p></div>

- item solto

  com parágrafo

  1. numerado dentro
"""


def test_native_docx_rich_markdown(tmp_path):
    import docx

    from markinho.exporter import export

    target = tmp_path / "rico.docx"
    export(MD_RICH, target, "docx", {"template": "abnt"}, backend="native")
    d = docx.Document(target)
    text = "\n".join(p.text for p in d.paragraphs)
    assert "Subtítulo nível 4" in text and "o site" in text and "[imagem: logo]" in text and "Bloco HTML" in text
    runs = [r for p in d.paragraphs for r in p.runs]
    assert any(r.font.strike for r in runs) and any(r.font.underline for r in runs)


@pytest.mark.parametrize("fmt", ["odt", "rst", "html", "docx"])
def test_pandoc_export(tmp_path, fmt):
    from markinho.exporter import FORMATS_BY_ID, export, format_backends

    if "pandoc" not in format_backends(FORMATS_BY_ID[fmt]):
        pytest.skip("Pandoc não instalado")
    target = tmp_path / ("saida" + FORMATS_BY_ID[fmt].ext)
    opts = {"title": "Relatório", "toc": True, "number_sections": True}
    if fmt == "docx":
        opts["template"] = "abnt"
    assert export(MD, target, fmt, opts, backend="pandoc", base_dir=tmp_path) == "pandoc"
    assert target.is_file() and target.stat().st_size > 50


def test_mcp_tools_info_list_and_export_rules(tmp_path, monkeypatch):
    pytest.importorskip("mcp")
    import asyncio

    from mcp.client import Client

    from markinho import mcp_server

    allowed = tmp_path / "permitida"
    (allowed / "sub").mkdir(parents=True)
    (allowed / "sub" / "nota.txt").write_text("olá")
    (allowed / ".oculta.txt").write_text("x")
    monkeypatch.setattr(mcp_server, "config_path", lambda: tmp_path / "mcp.json")
    monkeypatch.delenv("MARKINHO_MCP_FOLDERS", raising=False)
    monkeypatch.delenv("MARKINHO_MCP_ALLOW_WRITE", raising=False)
    mcp_server.save_config([str(allowed)], allow_write=True)

    def call(tool, args):
        async def go():
            async with Client(mcp_server.build_server()) as c:
                return await c.call_tool(tool, args)
        return asyncio.run(go())

    def text(res):
        return "".join(getattr(c, "text", "") for c in res.content)

    info = call("markinho_info", {})
    assert not info.is_error and str(allowed) in text(info) and '"write_allowed": true' in text(info).replace(" ", " ")
    res = call("list_documents", {"folder": str(allowed / "sub"), "recursive": False, "limit": 1})
    assert not res.is_error and "nota.txt" in text(res)
    res = call("list_documents", {})
    assert ".oculta" not in text(res)                               # arquivos ocultos não aparecem
    res = call("export_markdown", {"markdown": "# Oi", "output_path": str(allowed / "x.docx"), "format": "xyz"})
    assert res.is_error and "Formato desconhecido" in text(res)
    res = call("export_markdown", {"markdown": "# Oi", "output_path": str(allowed / "saida.txt"), "format": "html"})
    assert not res.is_error and (allowed / "saida.html").is_file()  # extensão corrigida para o formato
    res = call("export_markdown", {"markdown": "# Oi", "output_path": str(tmp_path / "fora.html"), "format": "html"})
    assert res.is_error and "fora das pastas" in text(res)


def test_strikethrough_outside_code_only():
    from markinho.exporter import markdown_to_html

    html = markdown_to_html("~~riscado~~ e `~~código~~`\n\n```\n~~bloco~~\n```")
    assert "<del>riscado</del>" in html and "<code>~~código~~</code>" in html and "~~bloco~~" in html
