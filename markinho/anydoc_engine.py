# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 dontstopbelieve — Markinho
"""Motor AnyDoc (Firecrawl, licença MIT): conversor em Rust, muito rápido.

Lê formatos que o motor nativo não lê — Word/Excel/PowerPoint antigos (.doc, .xls,
.ppt), OpenDocument (.odt/.ods/.odp), RTF — além de DOCX, XLSX, PPTX, EPUB, CSV e PDF.

Privacidade: o pacote Python do AnyDoc tem um modo de "OCR hospedado" que envia o
documento aos servidores da Firecrawl. O Markinho NUNCA usa esse modo: chama direto
as funções nativas em Rust (`anydoc._anydoc`), que não fazem nenhum acesso à rede.
PDFs escaneados são tratados pelo OCR local do Markinho (motor Nativo).

Em vez de usar o Markdown pronto do AnyDoc, o Markinho gera o texto a partir do modelo
do documento, para:
* colocar as imagens no lugar certo (salvas na pasta <nome>_assets/ ou em base64);
* gravar tabelas com células mescladas em HTML (rowspan/colspan);
* transformar "tabelas de layout" (caixas de texto) em texto corrido.
"""
from __future__ import annotations

import mimetypes
import re
from pathlib import Path
from typing import Any

# extensões documentadas pelo AnyDoc (o formato é detectado pelo conteúdo do arquivo)
EXTENSIONS = {".doc", ".docx", ".docm", ".dot", ".dotx", ".ppt", ".pps", ".pot", ".pptx", ".pptm", ".ppsx",
              ".ppsm", ".xls", ".xlsx", ".xlsm", ".xlsb", ".odt", ".ods", ".odp", ".rtf", ".epub", ".csv", ".pdf"}
_NO_MODEL = {".pdf"}                # PDF não tem modelo de documento: usa o Markdown direto
_PLACEHOLDERS = {"*", "<number>", "‹#›", "<#>", "<date/time>", "<footer>", "<header>"}
_VECTOR = {"image/x-emf", "image/emf", "image/x-wmf", "image/wmf"}   # formatos do Office que navegadores não exibem


def native():
    """Módulo nativo (Rust) — sem nenhum caminho de rede."""
    from anydoc import _anydoc

    return _anydoc


def version() -> str:
    try:
        from importlib.metadata import version as v

        return v("firecrawl-anydoc")
    except Exception:  # noqa: BLE001
        return ""


def convert(path: Path, opts: dict[str, Any], sink=None) -> str:
    nat = native()
    if path.suffix.lower() in _NO_MODEL:
        return nat.to_markdown(str(path))
    data = path.read_bytes()
    fmt = "csv" if path.suffix.lower() == ".csv" else None
    try:
        doc = nat.to_document(data, fmt)
    except Exception:  # noqa: BLE001  - formato sem modelo nesta versão: usa o Markdown pronto
        return nat.to_markdown(str(path))
    return Renderer(doc, sink, tables_html=bool(opts.get("tables_html", True))).render()


class Renderer:
    def __init__(self, doc, sink=None, tables_html: bool = True):
        self.doc = doc
        self.sink = sink if sink is not None and getattr(sink, "enabled", False) else None
        self.tables_html = tables_html
        self.assets = {a.id: a for a in doc.assets}
        self.used_notes: list[str] = []
        self.targets = self._link_targets(doc)       # âncoras usadas por links internos

    @classmethod
    def _link_targets(cls, doc) -> set[str]:
        found: set[str] = set()

        def inl(items):
            for i in items or []:
                if i.kind == "link" and i.target is not None and i.target.kind == "anchor":
                    found.add(i.target.value)
                if i.content:
                    inl(i.content)

        def blk(blocks):
            for b in blocks or []:
                inl(b.content)
                blk(b.blocks)
                if b.list:
                    for it in b.list.items:
                        blk(it.blocks)
                if b.table:
                    for row in b.table.grid:
                        for slot in row:
                            if slot.cell is not None:
                                blk(slot.cell.blocks)

        blk(doc.blocks)
        for n in doc.notes:
            blk(n.blocks)
        return found

    # ------------------------------------------------------------------ #
    def render(self) -> str:
        parts = [self.block(b) for b in self.doc.blocks]
        md = "\n\n".join(p for p in parts if p and p.strip())
        notes = {n.id: n for n in self.doc.notes}
        foot = []
        for nid in self.used_notes:
            n = notes.get(nid)
            if n is None:
                continue
            body = " ".join(self.block(b).replace("\n", " ") for b in n.blocks).strip()
            foot.append(f"[^{self._note_label(nid)}]: {body}")
        if foot:
            md += "\n\n" + "\n".join(foot)
        return md

    @staticmethod
    def _note_label(nid: str) -> str:
        return re.sub(r"[^\w-]+", "-", nid).strip("-") or "nota"

    # ------------------------------------------------------------------ #
    def inlines(self, items) -> str:
        # textos vizinhos com o mesmo estilo são unidos (o RTF quebra palavras em pedaços,
        # o que geraria "**Relat****ó****rio**")
        out: list[str] = []
        buf, style = "", None
        for i in items or []:
            if i.kind == "text":
                key = self._style_key(i.style)
                if buf and key == style:
                    buf += i.text or ""
                    continue
                if buf:
                    out.append(self._styled(buf, self._last_style))
                buf, style, self._last_style = i.text or "", key, i.style
                continue
            if buf:
                out.append(self._styled(buf, self._last_style))
                buf, style = "", None
            out.append(self.inline(i))
        if buf:
            out.append(self._styled(buf, self._last_style))
        return "".join(out)

    _last_style = None

    @staticmethod
    def _style_key(st):
        return None if st is None else (st.bold, st.italic, st.strike, st.code)

    def inline(self, i) -> str:
        k = i.kind
        if k == "text":
            return self._styled(i.text or "", i.style)
        if k == "link":
            text = self.inlines(i.content) or (i.target.value if i.target else "")
            t = i.target
            if t is None:
                return text
            url = "#" + t.value if t.kind == "anchor" else t.value
            return f"[{text}]({url})" if text.strip() else ""
        if k == "image":
            return self.image(i)
        if k == "anchor":
            return f'<a id="{i.anchor}"></a>' if i.anchor and i.anchor in self.targets else ""
        if k == "note_ref":
            if i.note_id is None:
                return ""
            if i.note_id not in self.used_notes:
                self.used_notes.append(i.note_id)
            return f"[^{self._note_label(i.note_id)}]"
        if k == "line_break":
            return "<br>"
        if k == "math":
            return f"${i.text or ''}$"
        if k == "checkbox":
            return "[x] " if i.checked else "[ ] "
        return i.text or ""

    @staticmethod
    def _styled(text: str, style) -> str:
        if not text or style is None or not text.strip():
            return text
        lead = text[: len(text) - len(text.lstrip())]
        trail = text[len(text.rstrip()):]
        core = text.strip()
        if style.code:
            return f"{lead}`{core}`{trail}"
        if style.strike:
            core = f"~~{core}~~"
        mark = "***" if style.bold and style.italic else "**" if style.bold else "*" if style.italic else ""
        return f"{lead}{mark}{core}{mark}{trail}"

    def image(self, i) -> str:
        alt = (i.alt or "").strip()
        src = i.source
        if src is not None and src.kind == "external" and src.url:
            return f"![{alt}]({src.url})"
        if src is not None and src.kind == "asset" and src.asset_id is not None:
            asset = self.assets.get(src.asset_id)
            if asset is not None and self.sink is not None and asset.media_type not in _VECTOR:
                ext = mimetypes.guess_extension(asset.media_type) or ".png"
                ref = self.sink.add(bytes(asset.data), ext, alt)
                if ref:
                    return ref
        return f"*[Imagem: {alt}]*" if alt else ""

    # ------------------------------------------------------------------ #
    def block(self, b, depth: int = 0) -> str:
        k = b.kind
        if k == "heading":
            text = self.inlines(b.content).strip()
            return ("#" * min(max(b.level or 1, 1), 6) + " " + text) if text else ""
        if k == "paragraph":
            text = self.inlines(b.content).strip()
            # marcadores vazios dos modelos do PowerPoint (nº do slide, data) não são conteúdo
            return "" if text in _PLACEHOLDERS else text
        if k == "list":
            return self.list_md(b.list, depth)
        if k == "table":
            return self.table(b.table)
        if k == "block_quote":
            inner = "\n\n".join(x for x in (self.block(c, depth) for c in b.blocks or []) if x)
            if not inner.strip():
                return ""
            return "\n".join("> " + ln if ln else ">" for ln in inner.split("\n"))
        if k == "code_block":
            text = (b.text or "").rstrip("\n")
            fence = "```"
            while fence in text:
                fence += "`"
            return f"{fence}{b.lang or ''}\n{text}\n{fence}"
        if k == "rule":
            return "---"
        if k == "math":
            return f"$$\n{(b.text or '').strip()}\n$$"
        return ""

    def list_md(self, lst, depth: int) -> str:
        if lst is None:
            return ""
        ordered = lst.marker != "bullet"
        lines = []
        for n, item in enumerate(lst.items):
            if ordered:
                marker = f"{(lst.start or 1) + n}."
            else:
                marker = "-"
            indent = " " * (len(marker) + 1)
            first = True
            for blk in item.blocks:
                text = self.block(blk, depth + 1)
                if not text:
                    continue
                if first:
                    head, *rest = text.split("\n")
                    lines.append(f"{marker} {head}")
                    lines += [indent + ln if ln else "" for ln in rest]
                    first = False
                else:
                    lines += [indent + ln if ln else "" for ln in text.split("\n")]
            if first:
                lines.append(marker)
        return "\n".join(lines)

    def _cell_text(self, cell) -> str:
        parts = [self.block(b) for b in cell.blocks]
        text = "<br>".join(p.replace("\n", "<br>") for p in parts if p)
        return text

    def table(self, t) -> str:
        if t is None or not t.grid:
            return ""
        if t.kind == "layout":
            # caixas de texto/posicionamento: o conteúdo vira texto corrido, célula a célula
            out = []
            for row in t.grid:
                for slot in row:
                    if slot.kind == "origin" and slot.cell is not None:
                        out += [x for x in (self.block(b) for b in slot.cell.blocks) if x]
            return "\n\n".join(out)
        merged = any(slot.kind == "origin" and slot.cell is not None and (slot.cell.row_span > 1 or slot.cell.col_span > 1)
                     for row in t.grid for slot in row)
        if merged and self.tables_html:
            from .assets import html_table

            rows = []
            for row in t.grid:
                r = []
                for slot in row:
                    if slot.kind != "origin" or slot.cell is None:
                        continue
                    r.append((self._cell_text(slot.cell), slot.cell.row_span, slot.cell.col_span))
                rows.append(r)
            return html_table(rows, header=True)   # 1ª linha como cabeçalho, igual à tabela Markdown
        from .converters import md_table

        texts: list[list[str]] = []
        for ri, row in enumerate(t.grid):
            r = []
            for slot in row:
                if slot.kind == "origin" and slot.cell is not None:
                    r.append(self._cell_text(slot.cell))
                else:   # coberta por mesclagem: repete o conteúdo da origem
                    o = t.grid[slot.origin_row][slot.origin_col] if slot.origin_row is not None else None
                    r.append(self._cell_text(o.cell) if o is not None and o.cell is not None else "")
            texts.append(r)
        return md_table(texts)
