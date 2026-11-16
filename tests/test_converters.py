"""Testes: gera arquivos de exemplo de cada formato e verifica a conversão."""
import json
import zipfile
from pathlib import Path

import pytest

from markinho import ConversionError, convert, supported_extensions


@pytest.fixture
def tmp(tmp_path: Path) -> Path:
    return tmp_path


def test_supported():
    for ext in (".pdf", ".docx", ".xlsx", ".pptx", ".html", ".csv", ".json", ".zip", ".epub"):
        assert ext in supported_extensions()


def test_csv(tmp):
    f = tmp / "dados.csv"
    f.write_text("nome;idade\nAna;30\nBruno;25\n", encoding="utf-8")
    md = convert(f).markdown
    assert "| nome | idade |" in md and "| Ana | 30 |" in md


def test_json(tmp):
    f = tmp / "a.json"
    f.write_text(json.dumps({"x": [1, 2]}))
    assert "```json" in convert(f).markdown


def test_html(tmp):
    f = tmp / "p.html"
    f.write_text("<html><head><title>T</title><script>x()</script></head>"
                 "<body><h1>Olá</h1><p>Um <b>teste</b></p><ul><li>a</li></ul></body></html>")
    md = convert(f).markdown
    assert "# Olá" in md and "**teste**" in md and "- a" in md and "x()" not in md


def test_docx(tmp):
    import docx
    d = docx.Document()
    d.add_heading("Relatório", 1)
    p = d.add_paragraph("Texto ")
    p.add_run("negrito").bold = True
    d.add_paragraph("item 1", style="List Bullet")
    d.add_paragraph("item 2", style="List Bullet")
    t = d.add_table(rows=2, cols=2)
    t.cell(0, 0).text, t.cell(0, 1).text, t.cell(1, 0).text, t.cell(1, 1).text = "A", "B", "1", "2"
    f = tmp / "r.docx"
    d.save(f)
    md = convert(f).markdown
    assert "# Relatório" in md and "**negrito**" in md
    assert "- item 1\n- item 2" in md and "| A | B |" in md


def test_xlsx(tmp):
    from openpyxl import Workbook
    wb = Workbook()
    ws = wb.active
    ws.title = "Vendas"
    ws.append(["Produto", "Qtd"])
    ws.append(["Café", 10])
    f = tmp / "v.xlsx"
    wb.save(f)
    md = convert(f).markdown
    assert "## Vendas" in md and "| Café | 10 |" in md


def test_pptx(tmp):
    from pptx import Presentation
    prs = Presentation()
    s = prs.slides.add_slide(prs.slide_layouts[1])
    s.shapes.title.text = "Introdução"
    s.placeholders[1].text = "Ponto principal"
    s.notes_slide.notes_text_frame.text = "Falar devagar"
    f = tmp / "s.pptx"
    prs.save(f)
    md = convert(f).markdown
    assert "## Slide 1: Introdução" in md and "Ponto principal" in md and "Falar devagar" in md


def test_pdf(tmp):
    # PDF mínimo com texto, escrito à mão
    content = b"BT /F1 24 Tf 72 720 Td (Ola PDF) Tj ET"
    objs = [b"<< /Type /Catalog /Pages 2 0 R >>",
            b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
            b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R "
            b"/Resources << /Font << /F1 5 0 R >> >> >>",
            b"<< /Length %d >>\nstream\n" % len(content) + content + b"\nendstream",
            b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>"]
    out, offs = b"%PDF-1.4\n", []
    for i, o in enumerate(objs, 1):
        offs.append(len(out))
        out += b"%d 0 obj\n" % i + o + b"\nendobj\n"
    xref = len(out)
    out += b"xref\n0 %d\n0000000000 65535 f \n" % (len(objs) + 1)
    out += b"".join(b"%010d 00000 n \n" % o for o in offs)
    out += b"trailer << /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF" % (len(objs) + 1, xref)
    f = tmp / "t.pdf"
    f.write_bytes(out)
    assert "Ola PDF" in convert(f).markdown


def test_zip(tmp):
    f = tmp / "pacote.zip"
    with zipfile.ZipFile(f, "w") as z:
        z.writestr("a.csv", "x,y\n1,2\n")
        z.writestr("b.txt", "olá")
    md = convert(f).markdown
    assert "## a.csv" in md and "| 1 | 2 |" in md and "olá" in md


def test_unsupported(tmp):
    f = tmp / "x.qwerty"
    f.write_text("?")
    with pytest.raises(ConversionError):
        convert(f)
