# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 dontstopbelieve — Markinho
"""Divisão do Markdown em pedaços ("chunks") para RAG / busca semântica.

Estratégias (inspiradas nas do Unstructured, implementadas do zero, sem dependências):

* ``title`` – cada seção (título + conteúdo) começa um pedaço novo; seções grandes são
  divididas e seções pequenas são unidas;
* ``page``  – um pedaço novo a cada página (precisa das marcas ``<!-- Página N -->``);
* ``basic`` – só preenche os pedaços até o tamanho máximo, sem olhar a estrutura.

Regras que valem para todas:

* tabelas e blocos de código nunca são cortados no meio; se forem maiores que o limite,
  a tabela é dividida por linhas **repetindo o cabeçalho** e o código, por linhas;
* parágrafos longos são divididos em frases/palavras, com sobreposição (``overlap``);
* cada pedaço leva o caminho de títulos (``headings``), a página, a origem e o
  tamanho aproximado em tokens.
"""
from __future__ import annotations

from .i18n import tr

import json
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Iterable

STRATEGIES = [("title", tr("Por título (seções)")), ("page", tr("Por página")), ("basic", tr("Só por tamanho"))]

_PAGE_RE = re.compile(r"^<!--\s*P[áa]gina\s+(\d+)\s*-->$", re.I)
_HEADING_START = re.compile(r"^(#{1,6})[ \t]+")


class _Heading:
    """Resultado no formato de `re.Match` (group 1 = ###, group 2 = texto), sem regex com retrocesso:
    a versão antiga, `(.*?)\\s*#*\\s*$`, demorava horas numa linha longa cheia de espaços."""

    def __init__(self, hashes: str, text: str):
        self._g = (None, hashes, text)

    def group(self, i: int = 0) -> str:
        return self._g[i]


class _HeadingRe:
    @staticmethod
    def match(line: str):
        m = _HEADING_START.match(line)
        if not m:
            return None
        text = line[m.end():].rstrip()
        closed = text.rstrip("#")                       # "## Título ##" → "Título"
        if closed != text and (not closed or closed[-1] in " \t"):
            text = closed.rstrip()
        return _Heading(m.group(1), text)


_HEADING_RE = _HeadingRe()
_FENCE_RE = re.compile(r"^(`{3,}|~{3,})")
_LIST_RE = re.compile(r"^\s*([-*+]|\d+[.)])\s+")


@dataclass
class Element:
    kind: str                 # heading | text | list | table | code | image | page
    text: str
    level: int = 0            # títulos
    page: int | None = None


@dataclass
class Chunk:
    id: str
    index: int
    text: str
    headings: list[str] = field(default_factory=list)
    page_start: int | None = None
    page_end: int | None = None
    kinds: list[str] = field(default_factory=list)
    chars: int = 0
    tokens: int = 0           # estimativa (≈ 4 caracteres por token)
    source: str = ""

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        return {k: v for k, v in d.items() if v not in (None, [], "")}


# --------------------------------------------------------------------------- #
# Markdown -> elementos
# --------------------------------------------------------------------------- #
def parse_elements(md: str) -> list[Element]:
    from .postprocess import strip_frontmatter

    lines = strip_frontmatter(md).split("\n")
    out: list[Element] = []
    page: int | None = None
    i, n = 0, len(lines)
    while i < n:
        line = lines[i]
        s = line.strip()
        if not s:
            i += 1
            continue
        m = _PAGE_RE.match(s)
        if m:
            page = int(m.group(1))
            out.append(Element("page", "", page=page))
            i += 1
            continue
        if s.startswith("<!--") and s.endswith("-->"):          # outros comentários: ignora
            i += 1
            continue
        fm = _FENCE_RE.match(s)
        if fm:                                                  # bloco de código inteiro
            fence = fm.group(1)
            j = i + 1
            while j < n and not lines[j].strip().startswith(fence[0] * len(fence)):
                j += 1
            out.append(Element("code", "\n".join(lines[i:j + 1]), page=page))
            i = j + 1
            continue
        hm = _HEADING_RE.match(s)
        if hm:
            out.append(Element("heading", s, level=len(hm.group(1)), page=page))
            i += 1
            continue
        if s.lower().startswith("<table"):                      # tabela HTML
            j = i
            while j < n and "</table>" not in lines[j].lower():
                j += 1
            out.append(Element("table", "\n".join(lines[i:j + 1]), page=page))
            i = j + 1
            continue
        if s.startswith("|"):                                   # tabela Markdown
            j = i
            while j < n and lines[j].strip().startswith("|"):
                j += 1
            out.append(Element("table", "\n".join(lines[i:j]), page=page))
            i = j
            continue
        if _LIST_RE.match(line):                                # lista (com itens aninhados)
            j = i + 1
            while j < n and lines[j].strip() and (_LIST_RE.match(lines[j]) or lines[j].startswith((" ", "\t"))):
                j += 1
            out.append(Element("list", "\n".join(lines[i:j]), page=page))
            i = j
            continue
        if re.match(r"^!\[[^\]]*\]\([^)]*\)$", s):              # imagem sozinha
            out.append(Element("image", s, page=page))
            i += 1
            continue
        j = i + 1                                               # parágrafo
        while j < n and lines[j].strip() and not (
                _HEADING_RE.match(lines[j].strip()) or _FENCE_RE.match(lines[j].strip())
                or lines[j].strip().startswith(("|", "<table", "<!--")) or _LIST_RE.match(lines[j])):
            j += 1
        out.append(Element("text", "\n".join(lines[i:j]), page=page))
        i = j
    return out


# --------------------------------------------------------------------------- #
# Divisão de elementos grandes
# --------------------------------------------------------------------------- #
def _split_text(text: str, size: int, overlap: int) -> list[str]:
    """Divide texto em pedaços ≤ size, preferindo fim de frase, com sobreposição."""
    if len(text) <= size:
        return [text]
    sentences = re.split(r"(?<=[.!?;:])\s+", text)
    pieces: list[str] = []
    for sent in sentences:               # frases maiores que o limite são quebradas por palavras
        while len(sent) > size:
            cut = sent.rfind(" ", 0, size)
            cut = cut if cut > size // 2 else size
            pieces.append(sent[:cut])
            sent = sent[cut:].lstrip()
        if sent:
            pieces.append(sent)
    out, cur = [], ""
    for p in pieces:
        if cur and len(cur) + 1 + len(p) > size:
            out.append(cur)
            tail = cur[-overlap:] if overlap else ""
            if tail and " " in tail:
                tail = tail[tail.index(" ") + 1:]
            cur = (tail + " " + p).strip() if tail else p
            if len(cur) > size:          # a sobreposição não pode estourar o limite
                cur = p
        else:
            cur = f"{cur} {p}".strip()
    if cur:
        out.append(cur)
    return out


def _split_table(text: str, size: int) -> list[str]:
    """Divide uma tabela grande por linhas, repetindo o cabeçalho em cada parte."""
    lines = text.split("\n")
    if text.lower().lstrip().startswith("<table"):
        head = [lines[0]] + ([lines[1]] if len(lines) > 1 and "<th" in lines[1].lower() else [])
        body = [ln for ln in lines[len(head):] if "</table>" not in ln.lower()]
        tail = ["</table>"]
    else:
        head = lines[:2] if len(lines) > 1 and re.match(r"^\|[\s:|-]+\|$", lines[1].strip()) else lines[:1]
        body = lines[len(head):]
        tail = []
    out, cur = [], []
    for row in body:
        if cur and len("\n".join(head + cur + [row] + tail)) > size:
            out.append("\n".join(head + cur + tail))
            cur = []
        cur.append(row)
    if cur or not out:
        out.append("\n".join(head + cur + tail))
    return out


def _split_code(text: str, size: int) -> list[str]:
    lines = text.split("\n")
    fence_open, fence_close = lines[0], lines[-1] if len(lines) > 1 else "```"
    body = lines[1:-1]
    out, cur = [], []
    for ln in body:
        if cur and len("\n".join([fence_open, *cur, ln, fence_close])) > size:
            out.append("\n".join([fence_open, *cur, fence_close]))
            cur = []
        cur.append(ln)
    out.append("\n".join([fence_open, *cur, fence_close]))
    return out


def _pieces(el: Element, size: int, overlap: int) -> list[str]:
    if len(el.text) <= size:
        return [el.text]
    if el.kind == "table":
        return _split_table(el.text, size)
    if el.kind == "code":
        return _split_code(el.text, size)
    if el.kind == "list":                # lista grande: divide entre itens
        items = re.split(r"\n(?=[-*+]\s|\d+[.)]\s)", el.text)
        out, cur = [], ""
        for it in items:
            if cur and len(cur) + 1 + len(it) > size:
                out.append(cur)
                cur = ""
            cur = f"{cur}\n{it}".strip("\n")
        out.append(cur)
        return [p for chunk in out for p in (_split_text(chunk, size, overlap) if len(chunk) > size else [chunk])]
    return _split_text(el.text, size, overlap)


# --------------------------------------------------------------------------- #
# Montagem dos chunks
# --------------------------------------------------------------------------- #
def chunk_markdown(md: str, max_chars: int = 1500, overlap: int = 150, strategy: str = "title",
                   combine_under: int = 300, include_headings: bool = True, overlap_all: bool = False,
                   source: str = "") -> list[Chunk]:
    """Divide `md` em pedaços.

    max_chars:        tamanho máximo de cada pedaço (caracteres).
    overlap:          caracteres repetidos do fim do pedaço anterior quando um texto longo é dividido.
    strategy:         "title", "page" ou "basic".
    combine_under:    (title) seções menores que isto são unidas à seguinte, se couberem.
    include_headings: repete o caminho de títulos no início de cada pedaço (melhora a busca).
    overlap_all:      aplica a sobreposição entre todos os pedaços, não só nos textos divididos.
    """
    max_chars = max(200, int(max_chars))
    overlap = max(0, min(int(overlap), max_chars // 2))
    elements = parse_elements(md)
    if strategy == "page" and not any(e.kind == "page" for e in elements):
        strategy = "title"   # sem marcas de página: cai para seções

    # 1) agrupa em seções
    sections: list[tuple[list[str], list[Element]]] = []
    path: list[tuple[int, str]] = []
    cur: list[Element] = []

    def flush():
        if cur:
            sections.append(([t for _, t in path], list(cur)))
            cur.clear()

    for el in elements:
        if el.kind == "page":
            if strategy == "page":
                flush()
            continue
        if el.kind == "heading":
            if strategy == "title":
                flush()
            text = _HEADING_RE.match(el.text).group(2)
            path = [(lv, t) for lv, t in path if lv < el.level] + [(el.level, text)]
            if strategy != "title":
                cur.append(el)
            continue
        cur.append(el)
    flush()

    # 2) une seções pequenas (estratégia por título)
    if strategy == "title" and combine_under > 0:
        merged: list[tuple[list[str], list[Element]]] = []
        for heads, els in sections:
            size = sum(len(e.text) for e in els)
            if merged:
                p_heads, p_els = merged[-1]
                p_size = sum(len(e.text) for e in p_els)
                if p_size < combine_under and p_size + size <= max_chars:
                    # inclui o título da seção unida para não perder o contexto
                    title_el = Element("heading", "#" * min(len(heads), 6) + " " + heads[-1]) if heads else None
                    merged[-1] = (p_heads, p_els + ([title_el] if title_el else []) + els)
                    continue
            merged.append((heads, els))
        sections = merged

    # 3) empacota os elementos de cada seção nos limites
    chunks: list[Chunk] = []
    for heads, els in sections:
        header = ""
        if include_headings and heads and strategy != "basic":
            header = " › ".join(heads)
        budget = max_chars - (len(header) + 2 if header else 0)
        budget = max(budget, max_chars // 2)
        buf: list[str] = []
        kinds: list[str] = []
        pages: list[int] = []

        def emit():
            if not buf:
                return
            body = "\n\n".join(buf)
            text = f"{header}\n\n{body}" if header else body
            chunks.append(Chunk("", 0, text, list(heads), min(pages) if pages else None,
                                max(pages) if pages else None, sorted(set(kinds))))
            buf.clear()
            kinds.clear()
            pages.clear()

        for el in els:
            for piece in _pieces(el, budget, overlap):
                size = sum(len(b) + 2 for b in buf)
                if buf and size + len(piece) > budget:
                    emit()
                buf.append(piece)
                kinds.append(el.kind)
                if el.page is not None:
                    pages.append(el.page)
        emit()

    # 4) sobreposição entre todos os pedaços (opcional) e numeração
    if overlap_all and overlap:
        for a, b in zip(chunks, chunks[1:]):
            tail = a.text[-overlap:]
            if " " in tail:
                tail = tail[tail.index(" ") + 1:]
            b.text = f"{tail}\n\n{b.text}" if len(tail) + len(b.text) <= max_chars + overlap else b.text
    stem = Path(source).stem if source else "doc"
    for k, c in enumerate(chunks):
        c.index = k
        c.id = f"{stem}-{k:04d}"
        c.chars = len(c.text)
        c.tokens = (len(c.text) + 3) // 4
        c.source = source
    return chunks


# --------------------------------------------------------------------------- #
# Saída
# --------------------------------------------------------------------------- #
def to_jsonl(chunks: Iterable[Chunk], metadata: dict[str, Any] | None = None) -> str:
    meta = {k: v for k, v in (metadata or {}).items() if v not in (None, "", [])}
    lines = []
    for c in chunks:
        d = c.to_dict()
        if meta:
            d["document"] = meta
        lines.append(json.dumps(d, ensure_ascii=False, default=str))
    return "\n".join(lines) + "\n"


def to_json(chunks: Iterable[Chunk], metadata: dict[str, Any] | None = None, settings: dict | None = None) -> str:
    data = {"document": {k: v for k, v in (metadata or {}).items() if v not in (None, "", [])},
            "settings": settings or {}, "chunks": [c.to_dict() for c in chunks]}
    return json.dumps(data, ensure_ascii=False, indent=2, default=str) + "\n"
