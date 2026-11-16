"""DOCX com controles de conteúdo (w:sdt), caixas de texto e tabelas-moldura; EPUB com imagens;
PDF com senha; tentativa automática com outro motor."""
import copy
import zipfile
from pathlib import Path

import docx
import pytest
from docx.oxml import parse_xml
from docx.oxml.ns import nsdecls

from markinho import ConversionError, convert
from markinho.postprocess import OutputOptions

W = nsdecls("w")


def _sdt(inner_xml: str) -> str:
    return f'<w:sdt {W}><w:sdtPr/><w:sdtContent>{inner_xml}</w:sdtContent></w:sdt>'


def _p(text: str) -> str:
    return f'<w:p {W}><w:r><w:t>{text}</w:t></w:r></w:p>'


def test_content_controls_paragraph_and_cells(tmp_path):
    d = docx.Document()
    d.add_paragraph("antes")
    d.element.body.insert(len(d.element.body) - 1, parse_xml(_sdt(_p("DENTRO DO CONTROLE"))))
    t = d.add_table(rows=1, cols=2)
    t.cell(0, 0).text = "Dono"
    tc = t.cell(0, 1)._tc
    wrapped = parse_xml(_sdt(f'<w:tc {W}><w:p><w:r><w:t>Fulano</w:t></w:r></w:p></w:tc>'))
    tc.addnext(wrapped)                                   # célula inteira dentro de um controle
    t.cell(0, 1).text = "2026"
    d.save(tmp_path / "sdt.docx")
    md = convert(tmp_path / "sdt.docx", "native").markdown
    assert "DENTRO DO CONTROLE" in md and "Fulano" in md and "Dono" in md


def test_textbox_without_fallback_duplicate(tmp_path):
    d = docx.Document()
    p = d.add_paragraph("corpo")
    box = parse_xml(
        f'<w:r {W} xmlns:mc="http://schemas.openxmlformats.org/markup-compatibility/2006">'
        f'<mc:AlternateContent><mc:Choice Requires="wps"><w:drawing><w:txbxContent>{_p("TEXTO DA CAIXA")}'
        f'</w:txbxContent></w:drawing></mc:Choice><mc:Fallback><w:pict><w:txbxContent>{_p("TEXTO DA CAIXA")}'
        f'</w:txbxContent></w:pict></mc:Fallback></mc:AlternateContent></w:r>')
    p._p.append(box)
    d.save(tmp_path / "box.docx")
    md = convert(tmp_path / "box.docx", "native").markdown
    assert md.count("TEXTO DA CAIXA") == 1 and "corpo" in md


def test_single_cell_layout_table(tmp_path):
    d = docx.Document()
    t = d.add_table(rows=1, cols=1)
    cell = t.cell(0, 0)
    cell.paragraphs[0].text = "item um"
    cell.paragraphs[0].style = d.styles["List Bullet"]
    cell.add_paragraph("item dois", style="List Bullet")
    inner = cell.add_table(rows=2, cols=2)
    for (r, c), v in {(0, 0): "A", (0, 1): "B", (1, 0): "1", (1, 1): "2"}.items():
        inner.cell(r, c).text = v
    d.save(tmp_path / "frame.docx")
    md = convert(tmp_path / "frame.docx", "native").markdown
    assert "- item um\n- item dois" in md and "| A | B |" in md and "| 1 | 2 |" in md


def test_epub_images_and_title(tmp_path):
    import io

    from PIL import Image

    buf = io.BytesIO()
    Image.new("RGB", (20, 20), "green").save(buf, "PNG")
    f = tmp_path / "livro.epub"
    with zipfile.ZipFile(f, "w") as z:
        z.writestr("mimetype", "application/epub+zip")
        z.writestr("META-INF/container.xml", '<?xml version="1.0"?><container xmlns="urn:oasis:names:tc:opendocument:'
                   'xmlns:container" version="1.0"><rootfiles><rootfile full-path="OEBPS/content.opf" '
                   'media-type="application/oebps-package+xml"/></rootfiles></container>')
        z.writestr("OEBPS/content.opf", '<?xml version="1.0"?><package xmlns="http://www.idpf.org/2007/opf" '
                   'version="3.0"><metadata xmlns:dc="http://purl.org/dc/elements/1.1/"><dc:title>Meu Livro'
                   '</dc:title></metadata><manifest><item id="c1" href="text/c1.xhtml" media-type="application/'
                   'xhtml+xml"/></manifest><spine><itemref idref="c1"/></spine></package>')
        z.writestr("OEBPS/text/c1.xhtml", '<html><body><h1>Capítulo 1</h1><p>Era uma vez.</p>'
                   '<img src="../images/fig.png" alt="Figura"/></body></html>')
        z.writestr("OEBPS/images/fig.png", buf.getvalue())
    r = convert(f, "native", output=OutputOptions(images="folder"))
    assert "# Meu Livro" in r.markdown and "Capítulo 1" in r.markdown and "Era uma vez." in r.markdown
    assert len(r.assets) == 1 and "](livro_assets/imagem_001.png)" in r.markdown


def test_password_pdf_message(tmp_path):
    pypdf = pytest.importorskip("pypdf")
    w = pypdf.PdfWriter()
    w.add_blank_page(200, 200)
    w.encrypt("segredo")
    with open(tmp_path / "s.pdf", "wb") as fh:
        w.write(fh)
    with pytest.raises(ConversionError, match="senha"):
        convert(tmp_path / "s.pdf")


def test_auto_fallback_to_other_engine(tmp_path, monkeypatch):
    from markinho.engines import ENGINES

    if not ENGINES["anydoc"].available()[0]:
        pytest.skip("AnyDoc não instalado")
    d = docx.Document()
    d.add_paragraph("conteúdo de teste")
    d.save(tmp_path / "x.docx")

    def boom(*a, **k):
        raise RuntimeError("falha simulada")

    monkeypatch.setattr(ENGINES["native"], "convert", boom)
    r = convert(tmp_path / "x.docx")
    assert "conteúdo de teste" in r.markdown and r.engine != "native" and "falha simulada" in r.warnings[0]
    with pytest.raises(ConversionError):
        convert(tmp_path / "x.docx", "native")              # motor escolhido à mão: sem tentativa extra
