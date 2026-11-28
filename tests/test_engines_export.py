import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import zipfile
from pathlib import Path

import pytest

from markinho import ConversionError, convert
from markinho.engines import AUTO, ENGINES, pick_engine
from markinho.exporter import available_formats, export, format_backends, FORMATS_BY_ID
from markinho.textfix import FixOptions

MD = "# Título\n\nTexto com **negrito** e *itálico*.\n\n- a\n  - b\n\n| x | y |\n|---|---|\n| 1 | 2 |\n"
has_pandoc = ENGINES["pandoc"].available()[0]


def test_auto_prefers_native(tmp_path):
    f = tmp_path / "a.csv"
    f.write_text("a,b\n1,2\n")
    assert pick_engine(f, AUTO).id == "native"


def test_unavailable_engine_message(tmp_path):
    """Motor não instalado não faz a conversão falhar: usa o automático e avisa (o aviso diz qual faltou)."""
    if not ENGINES["marker"].available()[0]:
        src = Path(__file__).resolve().parent.parent / "exemplos" / "relatorio.pdf"
        r = convert(src, "marker")
        assert r.markdown.strip() and any("Marker" in w for w in r.warnings)
        assert "pip install marker-pdf" in ENGINES["marker"].available()[1] + ENGINES["marker"].install_hint


def test_fix_applied_and_raw_kept(tmp_path):
    f = tmp_path / "t.txt"
    f.write_text("AvaliaÃ§Ã£o", encoding="utf-8")
    r = convert(f, fix=FixOptions())
    assert r.markdown.strip() == "Avaliação" and "Ã" in r.raw_markdown and r.fix_report.total
    assert convert(f).markdown.strip() == "AvaliaÃ§Ã£o"  # sem fix = texto original


def test_pdf_layout(tmp_path):
    pytest.importorskip("reportlab")
    pytest.importorskip("pdfplumber")
    from make_pdf import make_pdf

    md = convert(make_pdf(tmp_path / "r.pdf"), "native").markdown
    assert "# Relatório Anual de Vendas" in md
    assert "# Seção 2: Resultados" in md and "## Detalhes" in md
    assert "| Nordeste | 250 | 200 |" in md
    assert "Documento Interno" not in md and "Página 2" not in md   # cabeçalho/rodapé removidos
    only2 = convert(tmp_path / "r.pdf", "native", {"pages": "2"}).markdown
    assert "Seção 2" in only2 and "Seção 1" not in only2


@pytest.mark.skipif(not has_pandoc, reason="Pandoc não instalado")
def test_pandoc_engine(tmp_path):
    import docx
    d = docx.Document()
    d.add_heading("Olá", 1)
    d.add_paragraph("mundo")
    d.save(tmp_path / "a.docx")
    r = convert(tmp_path / "a.docx", "pandoc")
    assert r.engine == "pandoc" and "# Olá" in r.markdown


@pytest.mark.parametrize("fid", ["docx", "html", "pdf", "plain"])
def test_native_export(tmp_path, fid):
    fmt = FORMATS_BY_ID[fid]
    target = tmp_path / f"out{fmt.ext}"
    assert export(MD, target, fid, backend="native") == "native"
    assert target.stat().st_size > 40
    if fid == "plain":
        txt = target.read_text(encoding="utf-8")
        assert "Título" in txt and "**" not in txt and "|" not in txt
    if fid == "docx":
        import docx
        d = docx.Document(target)
        styles = [p.style.name for p in d.paragraphs]
        assert "Heading 1" in styles and "List Bullet 2" in styles and len(d.tables) == 1
    if fid == "pdf":
        assert target.read_bytes().startswith(b"%PDF")


@pytest.mark.skipif(not has_pandoc, reason="Pandoc não instalado")
def test_pandoc_export_all(tmp_path):
    for fmt in available_formats():
        if "pandoc" not in format_backends(fmt):
            continue
        target = tmp_path / f"{fmt.id}{fmt.ext}"
        assert export(MD, target, fmt.id, backend="pandoc") == "pandoc"
        assert target.stat().st_size > 0, fmt.id
    with zipfile.ZipFile(tmp_path / "docx.docx") as z:
        assert "Título" in z.read("word/document.xml").decode()
