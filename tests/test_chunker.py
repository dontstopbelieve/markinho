"""Pedaços para RAG: limites, tabelas, código, títulos, páginas e exportação."""
import json

from markinho.chunker import chunk_markdown, parse_elements, to_json, to_jsonl
from markinho.exporter import export

LONG = "Passo a passo da instalação do sistema. " * 60
TABLE = "| Col A | Col B |\n|---|---|\n" + "\n".join(f"| linha {i} | valor {i} |" for i in range(80))
MD = f"""---
title: "Manual"
---

# Manual

Introdução curta.

## Instalação

{LONG}

{TABLE}

```python
def f():
    return 1
```

## Uso

- item um
- item dois

<!-- Página 2 -->

### Detalhe

Texto final.
"""


def test_elements():
    kinds = [e.kind for e in parse_elements(MD)]
    assert kinds[:3] == ["heading", "text", "heading"] and "table" in kinds and "code" in kinds and "page" in kinds
    assert "title:" not in "".join(e.text for e in parse_elements(MD))       # frontmatter fica de fora


def test_limits_headings_and_tables():
    cs = chunk_markdown(MD, max_chars=600, overlap=80, source="manual.pdf")
    assert all(c.chars <= 600 for c in cs)
    assert cs[1].text.startswith("Manual › Instalação\n\n") and cs[1].headings == ["Manual", "Instalação"]
    tables = [c for c in cs if "table" in c.kinds]
    assert len(tables) >= 3 and all("| Col A | Col B |\n|---|---|" in c.text for c in tables)   # cabeçalho repetido
    code = [c for c in cs if "code" in c.kinds]
    assert code and "```python\ndef f():\n    return 1\n```" in code[0].text                    # código inteiro
    assert cs[0].id == "manual-0000" and [c.index for c in cs] == list(range(len(cs)))
    assert all(c.tokens == (c.chars + 3) // 4 for c in cs)


def test_overlap_on_split_text():
    cs = [c for c in chunk_markdown(MD, max_chars=600, overlap=80) if c.headings == ["Manual", "Instalação"]
          and c.kinds == ["text"]]
    a, b = cs[0].text.split("\n\n", 1)[1], cs[1].text.split("\n\n", 1)[1]
    assert a[-30:].strip() in b[:120]                                         # fim de um repete no início do outro


def test_small_sections_combined():
    cs = chunk_markdown(MD, max_chars=600, overlap=0)
    last = cs[-1]
    assert "item um" in last.text and "Texto final." in last.text and "### Detalhe" in last.text


def test_page_strategy_and_fallback():
    cs = chunk_markdown(MD, max_chars=2000, overlap=0, strategy="page")
    assert cs[-1].page_start == 2 and "Texto final." in cs[-1].text
    no_pages = MD.replace("<!-- Página 2 -->", "")
    assert chunk_markdown(no_pages, strategy="page")[0].headings == ["Manual"]   # sem marcas: por título


def test_basic_strategy_ignores_structure():
    cs = chunk_markdown("# A\n\ntexto a\n\n# B\n\ntexto b\n", max_chars=1000, strategy="basic")
    assert len(cs) == 1 and "# B" in cs[0].text


def test_json_outputs(tmp_path):
    cs = chunk_markdown(MD, max_chars=600)
    lines = to_jsonl(cs, {"title": "Manual"}).strip().split("\n")
    first = json.loads(lines[0])
    assert len(lines) == len(cs) and first["document"]["title"] == "Manual" and "text" in first
    data = json.loads(to_json(cs, {"title": "Manual"}, {"max_chars": 600}))
    assert data["settings"]["max_chars"] == 600 and len(data["chunks"]) == len(cs)
    out = tmp_path / "m.jsonl"
    assert export(MD, out, "chunks_jsonl", {"chunk_size": 600, "source": "manual.pdf"}) == "native"
    rows = [json.loads(x) for x in out.read_text(encoding="utf-8").splitlines()]
    assert rows[0]["id"] == "manual-0000" and rows[0]["source"] == "manual.pdf"
