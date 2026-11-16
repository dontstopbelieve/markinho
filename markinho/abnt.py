# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 dontstopbelieve — Markinho
"""Modelo de Word no padrão ABNT (NBR 14724 / 6024), usado na exportação para DOCX.

Folha A4; margens 3 cm (superior e esquerda) e 2 cm (inferior e direita); Times New Roman 12;
espaçamento 1,5; recuo de 1,25 cm na primeira linha; texto justificado; citações longas com recuo
de 4 cm, fonte 10 e espaçamento simples; títulos em preto (seção primária em negrito e maiúsculas,
secundária em maiúsculas, terciária em negrito, quaternária em itálico) e número de página no alto,
à direita.
"""
from __future__ import annotations

from pathlib import Path

FONT = "Times New Roman"


def _font(style, size=12, bold=None, italic=None, caps=None):
    from docx.oxml.ns import qn
    from docx.shared import Pt, RGBColor

    f = style.font
    f.name = FONT
    f.size = Pt(size)
    f.color.rgb = RGBColor(0, 0, 0)
    if bold is not None:
        f.bold = bold
    if italic is not None:
        f.italic = italic
    if caps is not None:
        f.all_caps = caps
    rpr = style.element.get_or_add_rPr()
    fonts = rpr.find(qn("w:rFonts"))
    if fonts is None:
        fonts = rpr.makeelement(qn("w:rFonts"), {})
        rpr.append(fonts)
    for attr in ("w:ascii", "w:hAnsi", "w:eastAsia", "w:cs"):
        fonts.set(qn(attr), FONT)
    for attr in ("w:asciiTheme", "w:hAnsiTheme", "w:eastAsiaTheme", "w:cstheme"):
        fonts.attrib.pop(qn(attr), None)


def _style(document, name, base="Normal"):
    from docx.enum.style import WD_STYLE_TYPE

    styles = document.styles
    try:
        return styles[name]
    except KeyError:
        st = styles.add_style(name, WD_STYLE_TYPE.PARAGRAPH)
        st.base_style = styles[base]
        return st


def _page_number(section) -> None:
    """Campo PAGE no cabeçalho, alinhado à direita."""
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn

    par = section.header.paragraphs[0] if section.header.paragraphs else section.header.add_paragraph()
    par.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    run = par.add_run()
    for tag, extra in (("w:fldChar", {"w:fldCharType": "begin"}), ("w:instrText", None),
                       ("w:fldChar", {"w:fldCharType": "end"})):
        el = OxmlElement(tag)
        if extra:
            for k, v in extra.items():
                el.set(qn(k), v)
        else:
            el.set(qn("xml:space"), "preserve")
            el.text = "PAGE"
        run._r.append(el)


def apply_abnt(document) -> None:
    """Aplica as regras ABNT aos estilos e às margens de um `docx.Document`."""
    from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_LINE_SPACING
    from docx.shared import Cm, Pt

    for sec in document.sections:
        sec.page_width, sec.page_height = Cm(21), Cm(29.7)
        sec.top_margin, sec.left_margin = Cm(3), Cm(3)
        sec.bottom_margin, sec.right_margin = Cm(2), Cm(2)
        sec.header_distance = Cm(2)
        if not any(p.text.strip() for p in sec.header.paragraphs) and "PAGE" not in sec.header._element.xml:
            _page_number(sec)

    def body(st):
        _font(st, 12)
        pf = st.paragraph_format
        pf.line_spacing_rule = WD_LINE_SPACING.ONE_POINT_FIVE
        pf.first_line_indent = Cm(1.25)
        pf.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        pf.space_before = Pt(0)
        pf.space_after = Pt(0)

    body(document.styles["Normal"])
    for name in ("Body Text", "First Paragraph", "Compact"):        # estilos usados pelo Pandoc
        body(_style(document, name))
    heads = {1: dict(bold=True, caps=True), 2: dict(bold=False, caps=True),
             3: dict(bold=True, caps=False), 4: dict(bold=False, caps=False, italic=True),
             5: dict(bold=False, caps=False, italic=True), 6: dict(bold=False, caps=False, italic=True)}
    for level, fmt in heads.items():
        st = _style(document, f"Heading {level}")
        _font(st, 12, bold=fmt["bold"], italic=fmt.get("italic", False), caps=fmt["caps"])
        pf = st.paragraph_format
        pf.alignment = WD_ALIGN_PARAGRAPH.LEFT
        pf.first_line_indent = Cm(0)
        pf.line_spacing_rule = WD_LINE_SPACING.ONE_POINT_FIVE
        pf.space_before = Pt(18)
        pf.space_after = Pt(18)
        pf.keep_with_next = True
    title = _style(document, "Title")
    _font(title, 12, bold=True, caps=True)
    title.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER
    title.paragraph_format.first_line_indent = Cm(0)
    for name in ("Quote", "Block Text", "Intense Quote"):               # citação longa (mais de 3 linhas)
        st = _style(document, name)
        _font(st, 10, italic=False)
        pf = st.paragraph_format
        pf.left_indent = Cm(4)
        pf.first_line_indent = Cm(0)
        pf.line_spacing_rule = WD_LINE_SPACING.SINGLE
        pf.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        pf.space_before = Pt(12)
        pf.space_after = Pt(12)
    for name in ("List Bullet", "List Number", "List Paragraph"):
        try:
            st = document.styles[name]
        except KeyError:
            continue
        _font(st, 12)
        st.paragraph_format.first_line_indent = Cm(0)
        st.paragraph_format.line_spacing_rule = WD_LINE_SPACING.ONE_POINT_FIVE


def number_headings(document) -> None:
    """Numeração progressiva das seções (1, 1.1, 1.1.1…), como pede a NBR 6024."""
    counters = [0] * 6
    for par in document.paragraphs:
        name = par.style.name if par.style is not None else ""
        if not name.startswith("Heading ") or not name[8:].isdigit() or not par.text.strip():
            continue
        lvl = int(name[8:])
        counters[lvl - 1] += 1
        for k in range(lvl, 6):
            counters[k] = 0
        num = ".".join(str(c) for c in counters[:lvl] if c) or str(counters[lvl - 1])
        if par.runs:
            par.runs[0].text = f"{num} " + par.runs[0].text
        else:
            par.add_run(f"{num} ")


def reference_docx(path: str | Path) -> Path:
    """Gera um .docx de referência com os estilos ABNT (para o Pandoc usar como modelo)."""
    import docx

    d = docx.Document()
    apply_abnt(d)
    d.save(str(path))
    return Path(path)
