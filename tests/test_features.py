"""Recursos da versão 3: colunas, código, imagens, OCR, tabelas mescladas, metadados e perfis."""
import json
import sys
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))

from markinho import convert  # noqa: E402
from markinho.assets import write_assets  # noqa: E402
from markinho.ocr import available_backends  # noqa: E402
from markinho.postprocess import OutputOptions  # noqa: E402

reportlab = pytest.importorskip("reportlab")
from make_pdf import make_columns_pdf, make_png, make_scanned_pdf  # noqa: E402

has_tesseract = "tesseract" in available_backends()


def test_columns_code_and_image(tmp_path):
    r = convert(make_columns_pdf(tmp_path / "c.pdf"))
    md = r.markdown
    left = md.index("Primeira coluna, parágrafo 3")
    right = md.index("Segunda coluna, parágrafo 1")
    assert left < right                                     # coluna esquerda inteira antes da direita
    assert "Texto de exemplo Segunda" not in md             # linhas das colunas não se misturam
    assert "```\ndef soma(a, b):\n    return a + b\n```" in md   # fonte monoespaçada -> código
    assert len(r.assets) == 1 and "](c_assets/imagem_001.png)" in md
    assert md.count("\n\nPrimeira coluna") == 3             # parágrafos separados


def test_columns_can_be_disabled(tmp_path):
    md = convert(make_columns_pdf(tmp_path / "c.pdf"), "native", {"pdf_columns": False}).markdown
    assert md.index("Segunda coluna, parágrafo 1") < md.index("Primeira coluna, parágrafo 3")


def test_margin_crop(tmp_path):
    from make_pdf import make_pdf

    md = convert(make_pdf(tmp_path / "r.pdf"), "native", {"pdf_strip_headers": False, "pdf_margin_top": 7,
                                                          "pdf_margin_bottom": 7}).markdown
    assert "Documento Interno" not in md and "Página 1" not in md and "Seção 1" in md


@pytest.mark.skipif(not has_tesseract, reason="Tesseract não instalado")
def test_scanned_pdf_ocr(tmp_path):
    r = convert(make_scanned_pdf(tmp_path / "s.pdf"))
    assert "Educação Ambiental" in r.markdown and "OCR" in r.markdown
    off = convert(tmp_path / "s.pdf", "native", {"ocr": "off"}).markdown
    assert "Educação" not in off


@pytest.mark.skipif(not has_tesseract, reason="Tesseract não instalado")
def test_image_ocr(tmp_path):
    r = convert(make_png(tmp_path / "t.png", "Relatório de Ação"))
    assert "Relatório de Ação" in r.markdown and len(r.assets) == 1


def _docx_with_merges(path: Path, png: Path) -> Path:
    import docx

    d = docx.Document()
    d.core_properties.author = "Ana Souza"
    d.add_heading("Relatório", 1)
    t = d.add_table(rows=3, cols=3)
    t.cell(0, 0).text = "Região"
    t.cell(0, 1).text = "Vendas"
    t.cell(0, 1).merge(t.cell(0, 2))
    t.cell(1, 0).text = "Sul"
    t.cell(1, 0).merge(t.cell(2, 0))
    for (r, c), v in {(1, 1): "10", (1, 2): "20", (2, 1): "30", (2, 2): "40"}.items():
        t.cell(r, c).text = v
    p = d.add_paragraph("Veja o ")
    d.add_picture(str(png))
    d.save(path)
    return path


def test_docx_merged_table_html_and_image(tmp_path):
    f = _docx_with_merges(tmp_path / "m.docx", make_png(tmp_path / "f.png", "X", (200, 100)))
    r = convert(f)
    assert '<th colspan="2">Vendas</th>' in r.markdown and '<td rowspan="2">Sul</td>' in r.markdown
    assert len(r.assets) == 1
    flat = convert(f, "native", {"tables_html": False}).markdown
    assert "| Região | Vendas | Vendas |" in flat and "<table>" not in flat


def test_pptx_and_xlsx_merges(tmp_path):
    from openpyxl import Workbook
    from pptx import Presentation
    from pptx.util import Inches

    prs = Presentation()
    s = prs.slides.add_slide(prs.slide_layouts[5])
    s.shapes.title.text = "Dados"
    tb = s.shapes.add_table(2, 3, Inches(1), Inches(2), Inches(6), Inches(1)).table
    tb.cell(0, 0).text = "Largo"
    tb.cell(0, 0).merge(tb.cell(0, 2))
    prs.save(tmp_path / "p.pptx")
    assert '<th colspan="3">Largo</th>' in convert(tmp_path / "p.pptx").markdown

    wb = Workbook()
    ws = wb.active
    ws.append(["Trimestre", None, "Total"])
    ws.merge_cells("A1:B1")
    ws.append(["T1", "T2", 30])
    wb.save(tmp_path / "x.xlsx")
    assert '<th colspan="2">Trimestre</th>' in convert(tmp_path / "x.xlsx").markdown


def test_image_modes_and_saving(tmp_path):
    f = _docx_with_merges(tmp_path / "m.docx", make_png(tmp_path / "f.png", "X", (200, 100)))
    folder = convert(f, output=OutputOptions(images="folder"))
    out = tmp_path / "out"
    out.mkdir()
    assert write_assets(folder.markdown, folder.assets, out) == 1
    assert (out / "m_assets" / "imagem_001.png").is_file()
    assert "data:image/png;base64," in convert(f, output=OutputOptions(images="base64")).markdown
    none = convert(f, output=OutputOptions(images="none"))
    assert "![" not in none.markdown and not none.assets


def test_frontmatter_and_profiles(tmp_path):
    f = _docx_with_merges(tmp_path / "m.docx", make_png(tmp_path / "f.png", "X", (200, 100)))
    md = convert(f, output=OutputOptions(frontmatter=True)).markdown
    assert md.startswith("---\n") and 'author: "Ana Souza"' in md and 'source: "m.docx"' in md
    obs = convert(f, output=OutputOptions(profile="obsidian")).markdown
    assert "![[imagem_001.png]]" in obs and '  - "markinho"' in obs
    llm = convert(f, output=OutputOptions(profile="llm")).markdown
    assert "![" not in llm and "<!--" not in llm
    out = tmp_path / "o"
    out.mkdir()
    r = convert(f, output=OutputOptions(profile="obsidian"))
    assert write_assets(r.markdown, r.assets, out) == 1     # imagens também saem no formato do Obsidian


def test_ollama_alt_text(tmp_path):
    class H(BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def do_GET(self):
            self.send_response(200)
            self.end_headers()
            self.wfile.write(json.dumps({"models": [{"name": "qwen2.5vl:3b"}]}).encode())

        def do_POST(self):
            body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            assert body["images"]
            self.send_response(200)
            self.end_headers()
            self.wfile.write(json.dumps({"response": "Um X preto em fundo branco."}).encode())

    srv = HTTPServer(("127.0.0.1", 0), H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    f = _docx_with_merges(tmp_path / "m.docx", make_png(tmp_path / "f.png", "X", (200, 100)))
    r = convert(f, output=OutputOptions(describe_images=True, ollama_url=f"http://127.0.0.1:{srv.server_port}"))
    srv.shutdown()
    assert "![Um X preto em fundo branco.](m_assets/imagem_001.png)" in r.markdown


def test_ollama_missing_is_warning_not_error(tmp_path):
    f = _docx_with_merges(tmp_path / "m.docx", make_png(tmp_path / "f.png", "X", (200, 100)))
    r = convert(f, output=OutputOptions(describe_images=True, ollama_url="http://127.0.0.1:9"))
    assert r.warnings and "Ollama" in r.warnings[0]


def test_cli_default_runs_terminal(tmp_path, capsys):
    from markinho.__main__ import cli

    f = tmp_path / "a.csv"
    f.write_text("a,b\n1,2\n")
    assert cli([str(f), "--frontmatter"]) == 0
    out = capsys.readouterr().out
    assert out.startswith("---") and "| 1 | 2 |" in out


def test_metadata_title_that_is_a_file_name_is_ignored():
    from markinho.postprocess import useful_title

    assert useful_title("LGPD_revisado 1.indd") == ""
    assert useful_title("Microsoft Word - contrato.docx") == ""
    assert useful_title(r"C:\Trabalhos\artigo.doc") == ""
    assert useful_title("Proteção de Dados na Igreja") == "Proteção de Dados na Igreja"
