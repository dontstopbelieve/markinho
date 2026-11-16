# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 dontstopbelieve — Markinho
"""Conversores de cada formato para Markdown.

Cada função recebe um `Path` e devolve uma string Markdown. As bibliotecas
externas são importadas dentro das funções, assim um formato sem dependência
instalada não impede os outros de funcionar.
"""
from __future__ import annotations

import csv
import io
import json
import re
import zipfile
from pathlib import Path
from typing import Iterable, Sequence

from .core import ConversionError, _REGISTRY, option, register


# --------------------------------------------------------------------------- #
# Utilitários
# --------------------------------------------------------------------------- #
def _read_text(path: Path) -> str:
    data = path.read_bytes()
    for enc in ("utf-8-sig", "cp1252", "latin-1"):
        try:
            return data.decode(enc)
        except UnicodeDecodeError:
            continue
    return data.decode("utf-8", errors="replace")


def _cell(value) -> str:
    if value is None:
        return ""
    if isinstance(value, float) and value.is_integer():
        value = int(value)
    text = str(value).replace("\r", "").replace("\n", "<br>")
    return text.replace("|", "\\|").strip()


def md_table(rows: Sequence[Sequence], header: bool = True) -> str:
    """Gera uma tabela Markdown a partir de uma lista de linhas."""
    rows = [list(r) for r in rows]
    # remove linhas totalmente vazias
    rows = [r for r in rows if any(_cell(c) for c in r)]
    if not rows:
        return ""
    width = max(len(r) for r in rows)
    # remove colunas vazias no fim
    while width > 1 and all(_cell(r[width - 1]) == "" for r in rows if len(r) >= width):
        width -= 1
    norm = [[_cell(c) for c in r[:width]] + [""] * (width - len(r[:width])) for r in rows]
    if header:
        head, body = norm[0], norm[1:]
    else:
        head, body = [f"Col {i + 1}" for i in range(width)], norm
    head = [h or " " for h in head]
    lines = ["| " + " | ".join(head) + " |", "|" + "|".join(["---"] * width) + "|"]
    lines += ["| " + " | ".join(r) + " |" for r in body]
    return "\n".join(lines)


def _fence(text: str, lang: str = "") -> str:
    ticks = "```"
    while ticks in text:
        ticks += "`"
    return f"{ticks}{lang}\n{text.rstrip()}\n{ticks}"


# --------------------------------------------------------------------------- #
# Texto simples
# --------------------------------------------------------------------------- #
@register("Texto", ".txt", ".md", ".markdown", ".rst", ".log")
def convert_text(path: Path) -> str:
    return _read_text(path)


_CODE_LANGS = {
    ".py": "python", ".js": "javascript", ".ts": "typescript", ".java": "java",
    ".c": "c", ".cpp": "cpp", ".cs": "csharp", ".go": "go", ".rs": "rust",
    ".rb": "ruby", ".php": "php", ".sh": "bash", ".sql": "sql", ".yaml": "yaml",
    ".yml": "yaml", ".toml": "toml", ".ini": "ini", ".css": "css",
}


@register("Código-fonte", *_CODE_LANGS)
def convert_code(path: Path) -> str:
    return f"# {path.name}\n\n" + _fence(_read_text(path), _CODE_LANGS[path.suffix.lower()])


@register("JSON", ".json")
def convert_json(path: Path) -> str:
    raw = _read_text(path)
    try:
        raw = json.dumps(json.loads(raw), indent=2, ensure_ascii=False)
    except json.JSONDecodeError:
        pass
    return f"# {path.name}\n\n" + _fence(raw, "json")


@register("XML", ".xml")
def convert_xml(path: Path) -> str:
    return f"# {path.name}\n\n" + _fence(_read_text(path), "xml")


# --------------------------------------------------------------------------- #
# CSV / TSV
# --------------------------------------------------------------------------- #
@register("CSV", ".csv", ".tsv")
def convert_csv(path: Path) -> str:
    text = _read_text(path)
    if path.suffix.lower() == ".tsv":
        delim = "\t"
    else:
        try:
            delim = csv.Sniffer().sniff(text[:4096], delimiters=",;\t|").delimiter
        except csv.Error:
            delim = ","
    rows = list(csv.reader(io.StringIO(text), delimiter=delim))
    return f"# {path.stem}\n\n" + md_table(rows)


# --------------------------------------------------------------------------- #
# HTML
# --------------------------------------------------------------------------- #
def html_to_markdown(html: str) -> str:
    from bs4 import BeautifulSoup
    from markdownify import markdownify

    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "noscript", "iframe", "svg", "head"]):
        tag.decompose()
    body = soup.body or soup
    md = markdownify(str(body), heading_style="ATX", bullets="-")
    title = soup.title.string.strip() if soup.title and soup.title.string else ""
    if title and not md.lstrip().startswith("#"):
        md = f"# {title}\n\n{md}"
    return md


@register("HTML", ".html", ".htm", ".xhtml")
def convert_html(path: Path) -> str:
    return html_to_markdown(_read_text(path))


# --------------------------------------------------------------------------- #
# PDF e imagens (implementados em pdf.py)
# --------------------------------------------------------------------------- #
@register("PDF", ".pdf")
def convert_pdf(path: Path) -> str:
    from .pdf import convert_pdf as _convert

    return _convert(path)


IMAGE_EXTS = (".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp", ".webp", ".gif")


@register("Imagem (OCR)", *IMAGE_EXTS)
def convert_image(path: Path) -> str:
    from .pdf import convert_image as _convert

    return _convert(path)


# --------------------------------------------------------------------------- #
# Tabelas com células mescladas
# --------------------------------------------------------------------------- #
def table_md(rows_spans: list[list[tuple[str, int, int]]], flat_rows: list[list[str]]) -> str:
    """Tabela Markdown simples; HTML com rowspan/colspan quando há mesclagem (opção)."""
    from .assets import has_merges, html_table

    if option("tables_html", True) and has_merges(rows_spans):
        return html_table(rows_spans)
    return md_table(flat_rows)


# --------------------------------------------------------------------------- #
# Word (.docx)
# --------------------------------------------------------------------------- #
_W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
_A_BLIP = ".//{http://schemas.openxmlformats.org/drawingml/2006/main}blip"
_R_EMBED = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}embed"


def _fmt_run(t: str, bold, italic, strike=False, code=False) -> str:
    stripped = t.strip()
    if not stripped:
        return t
    lead = t[: len(t) - len(t.lstrip())]
    trail = t[len(t.rstrip()):]
    if code:
        return f"{lead}`{stripped}`{trail}"
    mark = "***" if bold and italic else "**" if bold else "*" if italic else ""
    if strike:
        stripped = f"~~{stripped}~~"
    return f"{lead}{mark}{stripped}{mark}{trail}"


def _run_images(run, part) -> list[str]:
    from .core import current_sink

    sink = current_sink()
    out = []
    if sink is None or not sink.enabled:
        return out
    for blip in run._r.iterfind(_A_BLIP):
        rid = blip.get(_R_EMBED)
        try:
            img_part = part.related_parts[rid]
        except KeyError:
            continue
        descr = run._r.xpath(".//wp:docPr/@descr") or run._r.xpath(".//wp:docPr/@title") or [""]
        ext = Path(getattr(img_part, "partname", "x.png")).suffix or ".png"
        if ext.lower() in (".emf", ".wmf"):
            continue  # formatos vetoriais do Office que navegadores não exibem
        ref = sink.add(img_part.blob, ext, descr[0])
        if ref:
            out.append(ref)
    return out


def _runs_md(paragraph, part) -> str:
    parts: list[str] = []

    def do_run(run):
        font = run.font
        mono = (font.name or "").lower() in ("consolas", "courier new", "courier", "menlo", "monaco")
        parts.append(_fmt_run(run.text, run.bold, run.italic, bool(font.strike), mono))
        parts.extend(" " + r + " " for r in _run_images(run, part))

    inner = getattr(paragraph, "iter_inner_content", None)
    if inner is None:
        for run in paragraph.runs:
            do_run(run)
    else:
        for item in inner():
            if hasattr(item, "runs") and hasattr(item, "address"):   # hiperlink
                text = "".join(r.text for r in item.runs).strip()
                url = getattr(item, "url", "") or item.address
                if item.fragment and not url:
                    url = "#" + item.fragment
                parts.append(f"[{text}]({url})" if url and text else text)
            else:
                do_run(item)
    text = "".join(parts)
    return re.sub(r"\*\*\*\*|\*\*\s\*\*", " ", text).replace("  ", " ")


def _docx_paragraph(p, part) -> str:
    style = (p.style.name if p.style is not None else "") or ""
    low = style.lower()
    text = _runs_md(p, part).strip()
    plain = p.text.strip()
    if not text:
        return ""
    if low == "title":
        return f"# {plain}"
    if low.startswith(("heading", "título", "titulo")):
        digits = "".join(ch for ch in style if ch.isdigit())
        level = min(int(digits) if digits else 1, 6)
        return "#" * level + " " + (plain or text)
    numbered = p._p.pPr is not None and p._p.pPr.numPr is not None
    indent = 0
    if numbered and p._p.pPr.numPr.ilvl is not None:
        indent = int(p._p.pPr.numPr.ilvl.val or 0)
    if "list number" in low or "lista numerada" in low:
        return "   " * indent + f"1. {text}"
    if "list" in low or "lista" in low or numbered:
        return "  " * indent + f"- {text}"
    if low in ("quote", "intense quote", "citação", "citação intensa"):
        return f"> {text}"
    if "code" in low or "código" in low or "html preformatted" in low:
        return f"```\n{p.text}\n```"
    return text


_MC_FALLBACK = "{http://schemas.openxmlformats.org/markup-compatibility/2006}Fallback"


def _local(el) -> str:
    return el.tag.rsplit("}", 1)[-1] if isinstance(el.tag, str) else ""


def _row_cells(tr):
    """Células da linha, inclusive as envolvidas por controles de conteúdo (w:sdt)."""
    for child in tr.iterchildren():
        name = _local(child)
        if name == "tc":
            yield child
        elif name == "sdt":
            content = child.find(f"{_W}sdtContent")
            if content is not None:
                yield from (c for c in content.iterchildren() if _local(c) == "tc")


def _table_rows(tbl):
    for child in tbl.iterchildren():
        name = _local(child)
        if name == "tr":
            yield child
        elif name == "sdt":
            content = child.find(f"{_W}sdtContent")
            if content is not None:
                yield from (c for c in content.iterchildren() if _local(c) == "tr")


def _textboxes(p_el):
    """Conteúdo das caixas de texto de um parágrafo (ignora a cópia de compatibilidade mc:Fallback)."""
    for box in p_el.iter(f"{_W}txbxContent"):
        if any(a.tag == _MC_FALLBACK for a in box.iterancestors()):
            continue
        yield box


def _docx_blocks(container, document, part, in_cell: bool = False) -> list[str]:
    """Percorre parágrafos, tabelas, controles de conteúdo e caixas de texto, na ordem do documento."""
    from docx.text.paragraph import Paragraph

    blocks: list[str] = []
    for child in container.iterchildren():
        name = _local(child)
        if name == "p":
            md = _docx_paragraph(Paragraph(child, document), part)
            if md:
                blocks.append(md)
            for box in _textboxes(child):
                blocks += _docx_blocks(box, document, part, in_cell)
        elif name == "tbl":
            rows = list(_table_rows(child))
            cells = [list(_row_cells(tr)) for tr in rows]
            if len(rows) == 1 and len(cells[0]) == 1:
                # tabela de uma célula só = moldura de layout: o conteúdo vira texto normal
                blocks += _docx_blocks(cells[0][0], document, part, in_cell)
            else:
                blocks.append(_docx_table(child, document, part))
        elif name == "sdt":
            content = child.find(f"{_W}sdtContent")
            if content is not None:
                blocks += _docx_blocks(content, document, part, in_cell)
        elif name in ("customXml", "smartTag", "ins"):
            blocks += _docx_blocks(child, document, part, in_cell)
    return blocks


def _merge_lists(blocks: list[str]) -> list[str]:
    out: list[str] = []
    prev_list = False
    for md in blocks:
        is_list = bool(re.match(r"^\s*(- |\d+\. )", md))
        if is_list and prev_list:
            out[-1] += "\n" + md
        elif md.startswith("```") and out and out[-1].startswith("```") and out[-1].endswith("```"):
            out[-1] = out[-1][:-3] + md[4:]   # parágrafos de código seguidos = um bloco
        else:
            out.append(md)
        prev_list = is_list
    return out


def _cell_text(tc, document, part) -> str:
    parts = _docx_blocks(tc, document, part, in_cell=True)
    return "<br>".join(p.replace("\n", "<br>") for p in parts if p.strip())


def _docx_table(tbl, document, part) -> str:
    grid: list[list[tuple[int, int, str | None, str]]] = []   # (col, colspan, vmerge, texto)
    for tr in _table_rows(tbl):
        col, row = 0, []
        for tc in _row_cells(tr):
            span = tc.grid_span
            row.append((col, span, tc.vMerge, _cell_text(tc, document, part)))
            col += span
        if row:
            grid.append(row)
    spans: list[list[tuple[str, int, int]]] = []
    flat: list[list[str]] = []
    for r, row in enumerate(grid):
        srow, frow = [], []
        for col, span, vm, text in row:
            frow += [text] * span
            if vm == "continue":
                continue
            rowspan = 1
            if vm == "restart":
                for below in grid[r + 1:]:
                    hit = next((c for c in below if c[0] == col), None)
                    if hit and hit[2] == "continue":
                        rowspan += 1
                    else:
                        break
            srow.append((text, rowspan, span))
        spans.append(srow)
        flat.append(frow)
    # nas linhas "continue", repete o texto de cima na versão achatada
    for r in range(1, len(flat)):
        for col, span, vm, _t in grid[r]:
            if vm == "continue" and col < len(flat[r - 1]):
                for k in range(span):
                    if col + k < len(flat[r]):
                        flat[r][col + k] = flat[r - 1][col + k]
    return table_md(spans, flat)


@register("Word", ".docx")
def convert_docx(path: Path) -> str:
    import docx

    document = docx.Document(str(path))
    blocks = _merge_lists(_docx_blocks(document.element.body, document, document.part))
    if not blocks:
        return f"# {path.stem}\n"
    if not blocks[0].startswith("# "):
        title = document.core_properties.title
        if title:
            blocks.insert(0, f"# {title}")
    return "\n\n".join(blocks)


# --------------------------------------------------------------------------- #
# Excel
# --------------------------------------------------------------------------- #
@register("Excel", ".xlsx", ".xlsm")
def convert_xlsx(path: Path) -> str:
    from openpyxl import load_workbook

    # o modo completo (não read-only) é necessário para ler células mescladas
    full = path.stat().st_size < 15_000_000 and option("tables_html", True)
    wb = load_workbook(str(path), read_only=not full, data_only=True)
    parts = [f"# {path.stem}"]
    for ws in wb.worksheets:
        if getattr(ws, "sheet_state", "visible") != "visible":
            continue
        rows = [list(r) for r in ws.iter_rows(values_only=True)]
        merges = []
        if full and ws.merged_cells.ranges:
            r_off, c_off = (ws.min_row or 1), (ws.min_column or 1)
            for rng in ws.merged_cells.ranges:
                merges.append((rng.min_row - r_off, rng.min_col - c_off, rng.max_row - r_off, rng.max_col - c_off))
        if merges and rows:
            from .assets import spans_from_grid

            # remove linhas totalmente vazias do fim para não gerar tabelas enormes
            while rows and not any(v not in (None, "") for v in rows[-1]):
                rows.pop()
            table = table_md(spans_from_grid([[_cell(v) for v in r] for r in rows], merges), rows)
        else:
            table = md_table(rows)
        parts.append(f"## {ws.title}\n\n{table or '_Planilha vazia._'}")
    wb.close()
    return "\n\n".join(parts)


@register("Excel 97-2003", ".xls")
def convert_xls(path: Path) -> str:
    import xlrd

    try:   # formatting_info é necessário para ler as células mescladas
        book = xlrd.open_workbook(str(path), formatting_info=True)
    except Exception:  # noqa: BLE001  - alguns .xls não têm as informações de formatação
        book = xlrd.open_workbook(str(path))
    parts = [f"# {path.stem}"]
    for sheet in book.sheets():
        rows = [sheet.row_values(i) for i in range(sheet.nrows)]
        merges = [(rlo, clo, rhi - 1, chi - 1) for rlo, rhi, clo, chi in getattr(sheet, "merged_cells", [])
                  if rhi - rlo > 1 or chi - clo > 1]
        if merges and rows and option("tables_html", True):
            from .assets import spans_from_grid

            table = table_md(spans_from_grid([[_cell(v) for v in r] for r in rows], merges), rows)
        else:
            table = md_table(rows)
        parts.append(f"## {sheet.name}\n\n{table or '_Planilha vazia._'}")
    return "\n\n".join(parts)


# --------------------------------------------------------------------------- #
# PowerPoint
# --------------------------------------------------------------------------- #
def _pptx_table(table) -> str:
    spans: list[list[tuple[str, int, int]]] = []
    flat: list[list[str]] = []
    for r in table.rows:
        srow, frow = [], []
        for c in r.cells:
            frow.append(c.text)
            if c.is_spanned:
                continue
            if c.is_merge_origin:
                srow.append((c.text, c.span_height, c.span_width))
            else:
                srow.append((c.text, 1, 1))
        spans.append(srow)
        flat.append(frow)
    return table_md(spans, flat)


@register("PowerPoint", ".pptx")
def convert_pptx(path: Path) -> str:
    from pptx import Presentation
    from pptx.enum.shapes import MSO_SHAPE_TYPE

    from .core import current_sink

    sink = current_sink()
    prs = Presentation(str(path))
    parts = [f"# {prs.core_properties.title or path.stem}"]

    def shape_md(shape) -> Iterable[str]:
        if shape.shape_type == MSO_SHAPE_TYPE.GROUP:
            for s in sorted(shape.shapes, key=lambda s: ((s.top or 0), (s.left or 0))):
                yield from shape_md(s)
            return
        if getattr(shape, "has_table", False) and shape.has_table:
            yield _pptx_table(shape.table)
            return
        if shape.shape_type == MSO_SHAPE_TYPE.PICTURE or hasattr(shape, "image"):
            alt = shape._element.xpath(".//p:cNvPr/@descr")
            alt_text = alt[0] if alt and alt[0] else shape.name
            ref = ""
            if sink is not None and sink.enabled:
                try:
                    img = shape.image
                    ext = "." + (img.ext or "png")
                    if ext not in (".emf", ".wmf"):
                        ref = sink.add(img.blob, ext, alt_text)
                except Exception:  # noqa: BLE001
                    ref = ""
            if ref:
                yield ref
            elif alt and alt[0]:
                yield f"*[Imagem: {alt[0]}]*"
            return
        if getattr(shape, "has_chart", False) and shape.has_chart:
            try:
                chart = shape.chart
                cats = list(chart.plots[0].categories)
                rows = [["Série", *map(str, cats)]]
                for plot in chart.plots:
                    for series in plot.series:
                        rows.append([series.name, *series.values])
                title = chart.chart_title.text_frame.text if chart.has_title else "Gráfico"
                yield f"**{title}**\n\n" + md_table(rows)
            except Exception:  # noqa: BLE001
                yield "*[Gráfico]*"
            return
        if getattr(shape, "has_text_frame", False) and shape.has_text_frame:
            lines = []
            paras = [p for p in shape.text_frame.paragraphs if "".join(r.text for r in p.runs).strip()]
            for para in paras:
                t = "".join(_fmt_run(r.text, r.font.bold, r.font.italic) for r in para.runs).strip()
                lines.append("  " * para.level + f"- {t}" if len(paras) > 1 else t)
            if lines:
                yield "\n".join(lines)

    for i, slide in enumerate(prs.slides, 1):
        title_shape = slide.shapes.title
        title = title_shape.text.strip() if title_shape is not None and title_shape.has_text_frame else ""
        section = [f"## Slide {i}" + (f": {title}" if title else "")]
        # ordem de leitura: de cima para baixo, da esquerda para a direita
        def _pos(s):
            try:
                return ((s.top or 0) // 20, (s.left or 0))
            except Exception:  # noqa: BLE001
                return (0, 0)

        shapes = sorted(slide.shapes, key=_pos)
        for shape in shapes:
            try:
                if title_shape is not None and shape.shape_id == title_shape.shape_id:
                    continue
                section.extend(shape_md(shape))
            except Exception:  # noqa: BLE001  - forma que a biblioteca não reconhece: ignora só ela
                continue
        if slide.has_notes_slide:
            notes = slide.notes_slide.notes_text_frame.text.strip() if slide.notes_slide.notes_text_frame else ""
            if notes:
                section.append("### Notas\n\n" + notes)
        parts.append("\n\n".join(section))
    return "\n\n".join(parts)


# --------------------------------------------------------------------------- #
# EPUB (HTML compactado)
# --------------------------------------------------------------------------- #
@register("EPUB", ".epub")
def convert_epub(path: Path) -> str:
    import posixpath
    import xml.etree.ElementTree as ET

    from .safety import read_zip_member as _read

    with zipfile.ZipFile(path) as zf:
        container = ET.fromstring(_read(zf, "META-INF/container.xml"))
        opf_path = container.find(".//{*}rootfile").attrib["full-path"]
        opf = ET.fromstring(_read(zf, opf_path))
        base = posixpath.dirname(opf_path)
        manifest = {i.attrib["id"]: i.attrib["href"] for i in opf.iterfind(".//{*}item")}
        title_el = opf.find(".//{*}title")
        title = title_el.text.strip() if title_el is not None and title_el.text else path.stem
        names = set(zf.namelist())
        from .core import current_sink

        sink = current_sink()
        parts = []
        for ref in opf.iterfind(".//{*}itemref"):
            href = manifest.get(ref.attrib.get("idref", ""))
            if not href:
                continue
            chapter = posixpath.normpath(posixpath.join(base, href))
            if chapter not in names:
                continue
            md = html_to_markdown(_read(zf, chapter).decode("utf-8", "replace"))

            def img(m, _dir=posixpath.dirname(chapter)):
                src = posixpath.normpath(posixpath.join(_dir, m.group(2).split("#")[0]))
                if sink is not None and sink.enabled and src in names:
                    return sink.add(_read(zf, src), posixpath.splitext(src)[1] or ".png", m.group(1)) or m.group(0)
                return f"*[Imagem: {m.group(1)}]*" if m.group(1) else ""

            parts.append(re.sub(r"!\[([^\]]*)\]\(([^)\s]+)[^)]*\)", img, md))
        if not any(p.lstrip().startswith(f"# {title}") for p in parts[:2]):
            parts.insert(0, f"# {title}")
    return "\n\n".join(parts)


# --------------------------------------------------------------------------- #
# ZIP: converte cada arquivo suportado dentro do pacote
# --------------------------------------------------------------------------- #
@register("ZIP", ".zip")
def convert_zip(path: Path) -> str:
    import tempfile

    from .safety import read_zip_member

    parts = [f"# {path.name}"]
    with zipfile.ZipFile(path) as zf, tempfile.TemporaryDirectory() as tmp:
        for info in zf.infolist():
            name = Path(info.filename)
            if info.is_dir() or name.suffix.lower() not in _REGISTRY or name.suffix.lower() == ".zip":
                continue
            target = Path(tmp) / f"{len(parts)}{name.suffix}"
            target.write_bytes(read_zip_member(zf, info))     # nome próprio: nada sai da pasta temporária
            try:
                body = _REGISTRY[name.suffix.lower()].func(target)
            except Exception as exc:  # noqa: BLE001
                body = f"_Erro: {exc}_"
            parts.append(f"## {info.filename}\n\n{_demote(body)}")
    return "\n\n".join(parts)


def _demote(md: str) -> str:
    """Rebaixa os títulos em dois níveis para aninhar dentro de outra seção."""
    out = []
    in_code = False
    for line in md.splitlines():
        if line.startswith("```"):
            in_code = not in_code
        if not in_code and line.startswith("#"):
            line = ("##" + line) if line.count("#", 0, 6) <= 4 else line
        out.append(line)
    return "\n".join(out)
