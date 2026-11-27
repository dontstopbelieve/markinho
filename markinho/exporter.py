# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 dontstopbelieve — Markinho
"""Exportação de Markdown para outros formatos (o caminho inverso).

Usa o Pandoc quando disponível (dezenas de formatos). Sem Pandoc, há
exportadores nativos para HTML, DOCX, PDF (via Qt) e texto puro.
"""
from __future__ import annotations

import html as html_lib
import re
import shutil
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .engines import pandoc_formats, pandoc_path, run_pandoc


@dataclass(frozen=True)
class ExportFormat:
    id: str
    label: str
    ext: str
    pandoc: str | None        # nome do writer no Pandoc
    native: bool = False      # existe exportador nativo (sem Pandoc)
    binary: bool = False


FORMATS: list[ExportFormat] = [
    ExportFormat("docx", "Word (.docx)", ".docx", "docx", native=True, binary=True),
    ExportFormat("pdf", "PDF (.pdf)", ".pdf", "pdf", native=True, binary=True),
    ExportFormat("html", "Página web (.html)", ".html", "html5", native=True),
    ExportFormat("odt", "OpenDocument / LibreOffice (.odt)", ".odt", "odt", binary=True),
    ExportFormat("epub", "E-book EPUB (.epub)", ".epub", "epub3", binary=True),
    ExportFormat("pptx", "PowerPoint (.pptx) — um slide por título", ".pptx", "pptx", binary=True),
    ExportFormat("rtf", "Rich Text (.rtf)", ".rtf", "rtf"),
    ExportFormat("latex", "LaTeX (.tex)", ".tex", "latex"),
    ExportFormat("typst", "Typst (.typ)", ".typ", "typst"),
    ExportFormat("rst", "reStructuredText (.rst)", ".rst", "rst"),
    ExportFormat("asciidoc", "AsciiDoc (.adoc)", ".adoc", "asciidoc"),
    ExportFormat("mediawiki", "MediaWiki / Wikipédia (.wiki)", ".wiki", "mediawiki"),
    ExportFormat("org", "Emacs Org-mode (.org)", ".org", "org"),
    ExportFormat("textile", "Textile (.textile)", ".textile", "textile"),
    ExportFormat("jira", "Jira / Confluence (.jira)", ".jira", "jira"),
    ExportFormat("docbook", "DocBook 5 (.xml)", ".xml", "docbook5"),
    ExportFormat("ipynb", "Jupyter Notebook (.ipynb)", ".ipynb", "ipynb"),
    ExportFormat("gfm", "Markdown GitHub (.md)", ".md", "gfm"),
    ExportFormat("commonmark", "CommonMark (.md)", ".md", "commonmark"),
    ExportFormat("markdown_strict", "Markdown estrito (.md)", ".md", "markdown_strict"),
    ExportFormat("plain", "Texto puro (.txt)", ".txt", "plain", native=True),
    ExportFormat("chunks_jsonl", "Pedaços para RAG / IA (.jsonl)", ".jsonl", None, native=True),
    ExportFormat("chunks_json", "Pedaços para RAG / IA (.json)", ".json", None, native=True),
]
FORMATS_BY_ID = {f.id: f for f in FORMATS}

PDF_ENGINES = ["typst", "weasyprint", "wkhtmltopdf", "xelatex", "lualatex", "tectonic", "pdflatex"]

CSS = """
body{font-family:-apple-system,"Segoe UI",Roboto,"Helvetica Neue",Arial,sans-serif;line-height:1.6;
max-width:820px;margin:2rem auto;padding:0 1rem;color:#1f2328}
h1,h2,h3{line-height:1.25;margin-top:1.6em}h1{border-bottom:1px solid #d0d7de;padding-bottom:.3em}
table{border-collapse:collapse;margin:1em 0}th,td{border:1px solid #d0d7de;padding:6px 12px}
th{background:#f6f8fa}code{background:#f6f8fa;padding:.15em .35em;border-radius:4px;font-size:90%}
pre{background:#f6f8fa;padding:12px;border-radius:6px;overflow:auto}pre code{background:none;padding:0}
blockquote{border-left:4px solid #d0d7de;margin:0;padding:0 1em;color:#59636e}img{max-width:100%}
"""


def available_pdf_engines() -> list[str]:
    return [e for e in PDF_ENGINES if shutil.which(e)]


def format_backends(fmt: ExportFormat) -> list[str]:
    """Backends capazes de gerar o formato: 'pandoc' e/ou 'native'."""
    out = []
    if fmt.pandoc and pandoc_path() and fmt.pandoc in pandoc_formats("out"):
        if fmt.id != "pdf" or available_pdf_engines():
            out.append("pandoc")
    if fmt.native:
        out.append("native")
    return out


def available_formats() -> list[ExportFormat]:
    return [f for f in FORMATS if format_backends(f)]


def export(markdown: str, target: str | Path, fmt_id: str, options: dict[str, Any] | None = None,
           backend: str = "auto", base_dir: str | Path | None = None,
           allowed_dirs: list[Path] | None = None) -> str:
    """Exporta `markdown` para `target`. Devolve o backend usado ('pandoc' ou 'native').

    options: title, toc, number_sections, reference_doc, pdf_engine, template ("abnt" = Word no padrão ABNT).
    allowed_dirs: se informado (servidor MCP), só imagens locais dessas pastas entram no arquivo.
    O Markdown sempre passa por `sanitize.sanitize_markdown` (sem downloads e sem scripts).
    """
    from .sanitize import sanitize_markdown

    fmt = FORMATS_BY_ID[fmt_id]
    target = Path(target)
    opts = options or {}
    markdown, _notes = sanitize_markdown(markdown, base_dir or target.parent, allowed_dirs)
    backends = format_backends(fmt)
    if not backends:
        raise RuntimeError(f"Nenhum exportador disponível para {fmt.label}. Instale o Pandoc: pip install pypandoc_binary")
    if backend == "auto":
        backend = backends[0]
    elif backend not in backends:
        raise RuntimeError(f"O exportador '{backend}' não gera {fmt.label}.")
    if backend == "pandoc":
        _export_pandoc(markdown, target, fmt, opts, base_dir)
    else:
        _NATIVE[fmt.id](markdown, target, opts)
    return backend


# --------------------------------------------------------------------------- #
# Pandoc
# --------------------------------------------------------------------------- #
def _export_pandoc(md: str, target: Path, fmt: ExportFormat, opts: dict, base_dir) -> None:
    args = ["-f", "markdown+pipe_tables+tex_math_dollars-raw_tex", "-t", fmt.pandoc, "-o", str(target)]
    title = opts.get("title") or _first_heading(md) or target.stem
    standalone = fmt.binary or fmt.id in ("html", "latex", "rtf", "typst", "docbook")
    if standalone:
        args.append("-s")
        # em DOCX/ODT/PPTX o título só entra se o usuário pedir (senão duplicaria o "# Título")
        if fmt.id not in ("docx", "odt", "pptx") or opts.get("title"):
            args += ["--metadata", f"title={title}"]
    if opts.get("toc"):
        args.append("--toc")
    if opts.get("number_sections"):
        args.append("--number-sections")
    abnt_ref = None
    if opts.get("reference_doc") and fmt.id in ("docx", "odt", "pptx"):
        args.append(f"--reference-doc={opts['reference_doc']}")
    elif opts.get("template") == "abnt" and fmt.id == "docx":
        from .abnt import reference_docx

        abnt_ref = Path(tempfile.mkstemp(suffix=".docx")[1])
        reference_docx(abnt_ref)
        args.append(f"--reference-doc={abnt_ref}")
    if base_dir:
        args.append(f"--resource-path={base_dir}")
    css_file = None
    if fmt.id in ("html", "epub") or (fmt.id == "pdf" and opts.get("pdf_engine", "") in ("weasyprint", "wkhtmltopdf")):
        css_file = Path(tempfile.mkstemp(suffix=".css")[1])
        css_file.write_text(CSS, encoding="utf-8")
        args.append(f"--css={css_file}")
        if fmt.id == "html":
            args.append("--embed-resources")
    if fmt.id == "pdf":
        engines = available_pdf_engines()
        eng = opts.get("pdf_engine") if opts.get("pdf_engine") in engines else engines[0]
        args.append(f"--pdf-engine={eng}")
        if eng in ("xelatex", "lualatex"):
            args += ["-V", "geometry:margin=2.5cm", "-V", "mainfont=DejaVu Serif"]
    try:
        run_pandoc(args, input_text=md)
    except RuntimeError as exc:
        if "--embed-resources" in args and "embed-resources" in str(exc):
            args[args.index("--embed-resources")] = "--self-contained"  # Pandoc < 2.19
            run_pandoc(args, input_text=md)
        else:
            raise
    finally:
        if css_file:
            css_file.unlink(missing_ok=True)
        if abnt_ref:
            abnt_ref.unlink(missing_ok=True)
    if opts.get("template") == "abnt" and fmt.id == "docx" and target.exists():
        import docx

        d = docx.Document(str(target))       # garante margens e número de página (o Pandoc não copia o cabeçalho)
        from .abnt import apply_abnt

        apply_abnt(d)
        d.save(str(target))


def _first_heading(md: str) -> str:
    for line in md.splitlines():
        if line.startswith("# "):
            return line[2:].strip()
    return ""


# --------------------------------------------------------------------------- #
# Nativos
# --------------------------------------------------------------------------- #
_LIST_RE = re.compile(r"^( *)([-*+]|\d+[.)])( +)")


def _fix_list_indent(md: str) -> str:
    """Reindenta listas aninhadas com 2/3 espaços (GFM) para 4 espaços (python-markdown)."""
    out, stack, in_code = [], [], False
    for line in md.split("\n"):
        if line.lstrip().startswith(("```", "~~~")):
            in_code = not in_code
        m = None if in_code else _LIST_RE.match(line)
        if m:
            ind = len(m.group(1))
            while stack and stack[-1] > ind:
                stack.pop()
            if not stack or stack[-1] < ind:
                stack.append(ind)
            line = " " * (4 * (len(stack) - 1)) + line[ind:]
        elif not line.strip():
            pass
        elif not line.startswith(" "):
            stack = []
        out.append(line)
    return "\n".join(out)


_STRIKE = re.compile(r"~~(?=\S)([^~\n]{1,500})~~")


def _strikethrough(html: str) -> str:
    """~~riscado~~ (GFM) vira <del>, fora de blocos de código (a biblioteca markdown não faz isso)."""
    if "~~" not in html:
        return html
    out, depth = [], 0
    for part in re.split(r"(<pre\b|</pre>|<code\b|</code>)", html):
        if part in ("<pre", "<code"):
            depth += 1
        elif part in ("</pre>", "</code>"):
            depth = max(0, depth - 1)
        elif depth == 0:
            part = _STRIKE.sub(r"<del>\1</del>", part)
        out.append(part)
    return "".join(out)


def markdown_to_html(md: str, toc: bool = False, highlight: bool = False) -> str:
    """Markdown -> fragmento HTML (biblioteca `markdown`; sem ela, usa o Qt).
    `highlight`: blocos de código coloridos (Pygments, cores embutidas — funciona no Qt e no HTML)."""
    md = _fix_list_indent(md)
    try:
        import markdown as mdlib

        exts = ["extra", "sane_lists"] + (["toc"] if toc else [])
        cfg = {}
        if highlight:
            try:
                import pygments  # noqa: F401

                exts.append("codehilite")
                cfg = {"codehilite": {"noclasses": True, "guess_lang": False, "pygments_style": "default"}}
            except ImportError:
                pass
        body = _strikethrough(mdlib.markdown(md, extensions=exts, extension_configs=cfg, output_format="html"))
        if toc:
            conv = mdlib.Markdown(extensions=["extra", "toc"])
            conv.convert(md)
            body = f'<nav class="toc">{conv.toc}</nav>\n{body}'
        return body
    except ImportError:
        from PySide6.QtGui import QTextDocument

        _qt_app()
        doc = QTextDocument()
        doc.setMarkdown(md)
        return doc.toHtml()


def html_page(md: str, title: str = "", toc: bool = False) -> str:
    title = title or _first_heading(md) or "Documento"
    return (f'<!DOCTYPE html>\n<html lang="pt-BR"><head><meta charset="utf-8">'
            f'<meta name="viewport" content="width=device-width,initial-scale=1">'
            f"<title>{html_lib.escape(title)}</title><style>{CSS}</style></head>\n"
            f"<body>\n{markdown_to_html(md, toc, highlight=True)}\n</body></html>\n")


def _native_html(md: str, target: Path, opts: dict) -> None:
    target.write_text(html_page(md, opts.get("title", ""), bool(opts.get("toc"))), encoding="utf-8")


def _native_plain(md: str, target: Path, opts: dict) -> None:
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(markdown_to_html(md), "html.parser")
    for br in soup.find_all(["p", "li", "h1", "h2", "h3", "h4", "h5", "h6", "tr", "pre"]):
        br.append("\n")
    for td in soup.find_all(["td", "th"]):
        td.append("\t")
    text = soup.get_text()
    from .core import normalize

    target.write_text(normalize(text), encoding="utf-8")


def _qt_app():
    from PySide6.QtGui import QGuiApplication

    app = QGuiApplication.instance()
    if app is None:
        import os
        import sys

        if sys.platform.startswith("linux") and not os.environ.get("DISPLAY") and not os.environ.get("WAYLAND_DISPLAY"):
            os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        # QApplication (e não só QGuiApplication): se depois a interface for aberta no mesmo processo,
        # ela precisa da versão completa
        from PySide6.QtWidgets import QApplication

        app = QApplication([])
    return app


def _native_pdf(md: str, target: Path, opts: dict) -> None:
    """Markdown -> HTML -> PDF usando o motor de texto do Qt (não precisa de LaTeX)."""
    from PySide6.QtCore import QMarginsF, QSizeF
    from PySide6.QtGui import QPageLayout, QPageSize, QPdfWriter, QTextDocument

    _qt_app()
    css = ("body{font-family:'DejaVu Sans',Arial,sans-serif;font-size:10.5pt}"
           "h1{font-size:20pt}h2{font-size:16pt}h3{font-size:13pt}"
           "table{border-collapse:collapse}th,td{border:1px solid #888;padding:4px}"
           "th{background:#eee}pre{background:#f4f4f4;font-family:monospace}code{font-family:monospace}")
    doc = QTextDocument()
    doc.setDefaultStyleSheet(css)
    body = markdown_to_html(md, bool(opts.get("toc")))
    # o Qt não aplica bordas de CSS em tabelas; usa os atributos HTML antigos
    body = body.replace("<table>", '<table border="1" cellspacing="0" cellpadding="5">')
    doc.setHtml(body)
    writer = QPdfWriter(str(target))
    writer.setPageSize(QPageSize(QPageSize.A4))
    writer.setPageMargins(QMarginsF(20, 20, 20, 20), QPageLayout.Millimeter)
    writer.setResolution(96)  # mesma resolução lógica da tela: fontes em pt saem no tamanho certo
    writer.setTitle(opts.get("title") or _first_heading(md) or target.stem)
    writer.setCreator("Markinho")
    doc.documentLayout().setPaintDevice(writer)
    doc.setPageSize(QSizeF(writer.width(), writer.height()))
    doc.print_(writer)


def _native_docx(md: str, target: Path, opts: dict) -> None:
    """Markdown -> HTML -> DOCX com python-docx (títulos, listas, tabelas, código, citações)."""
    import docx
    from bs4 import BeautifulSoup, NavigableString, Tag
    from docx.shared import Pt, RGBColor

    document = docx.Document(opts["reference_doc"]) if opts.get("reference_doc") else docx.Document()
    cp = document.core_properties          # nada de “python-docx” nem autor do modelo no arquivo novo
    cp.author, cp.last_modified_by, cp.comments = "", "", ""
    if opts.get("title"):
        cp.title = opts["title"]
    soup = BeautifulSoup(markdown_to_html(md), "html.parser")

    def add_inline(par, node, bold=False, italic=False, code=False, strike=False):
        for child in node.children:
            if isinstance(child, NavigableString):
                text = str(child)
                if not text:
                    continue
                if not code:
                    text = text.replace("\n", " ")
                run = par.add_run(text)
                run.bold, run.italic = bold or None, italic or None
                if strike:
                    run.font.strike = True
                if code:
                    run.font.name = "Consolas"
                    run.font.size = Pt(9.5)
            elif isinstance(child, Tag):
                name = child.name
                if name == "br":
                    par.add_run().add_break()
                elif name == "img":
                    par.add_run(f"[imagem: {child.get('alt', '')}]").italic = True
                elif name == "a":
                    before = len(par.runs)
                    add_inline(par, child, bold, italic, code, strike)
                    for r in par.runs[before:]:
                        r.font.underline = True
                        r.font.color.rgb = RGBColor(0x05, 0x63, 0xC1)
                else:
                    add_inline(par, child,
                               bold or name in ("strong", "b"),
                               italic or name in ("em", "i"),
                               code or name == "code",
                               strike or name in ("del", "s"))

    def style_or(name: str, fallback: str = "Normal"):
        try:
            document.styles[name]
            return name
        except KeyError:
            return fallback

    def add_list(tag, level=0):
        ordered = tag.name == "ol"
        base = "List Number" if ordered else "List Bullet"
        style = style_or(base if level == 0 else f"{base} {min(level + 1, 3)}", base)
        for li in tag.find_all("li", recursive=False):
            par = document.add_paragraph(style=style)
            nested = []
            for child in list(li.children):
                if isinstance(child, Tag) and child.name in ("ul", "ol"):
                    nested.append(child)
                    child.extract()
            # <li><p>…</p></li> em listas "soltas"
            if li.find("p", recursive=False):
                for p in li.find_all("p", recursive=False):
                    add_inline(par, p)
            else:
                add_inline(par, li)
            for n in nested:
                add_list(n, level + 1)

    def walk(container):
        for el in container.children:
            if not isinstance(el, Tag):
                if str(el).strip():
                    document.add_paragraph(str(el).strip())
                continue
            name = el.name
            if name in ("h1", "h2", "h3", "h4", "h5", "h6"):
                level = int(name[1])
                h = document.add_heading(level=min(level, 9))
                add_inline(h, el)
            elif name == "p":
                par = document.add_paragraph()
                add_inline(par, el)
            elif name in ("ul", "ol"):
                add_list(el)
            elif name == "pre":
                par = document.add_paragraph(style=style_or("No Spacing"))
                run = par.add_run(el.get_text().rstrip("\n"))
                run.font.name = "Consolas"
                run.font.size = Pt(9.5)
            elif name == "blockquote":
                for p in el.find_all(["p"]) or [el]:
                    par = document.add_paragraph(style=style_or("Quote"))
                    add_inline(par, p)
            elif name == "table":
                rows = el.find_all("tr")
                ncols = max((len(r.find_all(["td", "th"])) for r in rows), default=0)
                if not rows or not ncols:
                    continue
                table = document.add_table(rows=len(rows), cols=ncols)
                table.style = style_or("Table Grid", None) if style_or("Table Grid", "") else None
                for i, r in enumerate(rows):
                    for j, cell in enumerate(r.find_all(["td", "th"])):
                        par = table.cell(i, j).paragraphs[0]
                        add_inline(par, cell, bold=cell.name == "th")
            elif name == "hr":
                document.add_paragraph("―" * 20)
            elif name in ("div", "section", "nav", "article"):
                walk(el)
            else:
                par = document.add_paragraph()
                add_inline(par, el)

    walk(soup)
    if opts.get("template") == "abnt":
        from .abnt import apply_abnt, number_headings

        apply_abnt(document)
        if opts.get("number_sections"):
            number_headings(document)
    document.save(str(target))


def _chunk_settings(opts: dict) -> dict:
    return {"max_chars": int(opts.get("chunk_size", 1500) or 1500),
            "overlap": int(opts.get("chunk_overlap", 150) or 0),
            "strategy": opts.get("chunk_by", "title") or "title",
            "include_headings": bool(opts.get("chunk_headings", True))}


def _native_chunks(md: str, target: Path, opts: dict, fmt: str) -> None:
    from .chunker import chunk_markdown, to_json, to_jsonl

    settings = _chunk_settings(opts)
    chunks = chunk_markdown(md, source=opts.get("source", "") or target.stem, **settings)
    meta = dict(opts.get("metadata") or {})
    if opts.get("source"):
        meta.setdefault("source", opts["source"])
    text = to_jsonl(chunks, meta) if fmt == "jsonl" else to_json(chunks, meta, settings)
    target.write_text(text, encoding="utf-8")


_NATIVE = {"html": _native_html, "docx": _native_docx, "pdf": _native_pdf, "plain": _native_plain,
           "chunks_jsonl": lambda md, t, o: _native_chunks(md, t, o, "jsonl"),
           "chunks_json": lambda md, t, o: _native_chunks(md, t, o, "json")}
