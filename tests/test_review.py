"""Avisos com páginas a revisar, progresso por página, parar no meio e limpeza de carimbos (PJe/SEI)."""
import sys
import threading
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))
from markinho import convert  # noqa: E402
from markinho.core import CANCELLED, ConversionError  # noqa: E402

reportlab = pytest.importorskip("reportlab")
from make_pdf import make_pdf, make_pje_pdf, make_scanned_pdf  # noqa: E402


def test_pje_stamps_removed(tmp_path):
    pdf = make_pje_pdf(tmp_path / "processo.pdf")
    md = convert(pdf, "native").markdown
    assert "parágrafo 12" in md and "SENTENÇA" in md
    assert "Assinado eletronicamente" not in md and "Num. 98765" not in md and "pje.tjxx" not in md
    r = convert(pdf, "native")
    assert any("Carimbos" in w for w in r.warnings)
    kept = convert(pdf, "native", {"pdf_strip_stamps": False, "pdf_strip_headers": False}).markdown
    assert "Num. 98765" in kept


def test_progress_reported_per_page(tmp_path):
    pdf = make_pdf(tmp_path / "doc.pdf", pages=4)
    seen = []
    convert(pdf, "native", progress=lambda d, t: seen.append((d, t)))
    assert seen[0] == (0, 4) and seen[-1] == (4, 4)


def test_cancel_stops_conversion(tmp_path):
    pdf = make_pdf(tmp_path / "doc.pdf", pages=4)
    ev = threading.Event()

    def prog(done, total):
        if done == 1:
            ev.set()

    with pytest.raises(ConversionError, match=CANCELLED):
        convert(pdf, "auto", progress=prog, cancel=ev)


def test_scanned_without_ocr_lists_pages_to_review(tmp_path):
    r = convert(make_scanned_pdf(tmp_path / "s.pdf"), "native", {"ocr": "off"})
    assert r.review_pages == [1]
    assert any("Nenhum texto reconhecido" in w for w in r.warnings)


def test_booklet_sections_are_headings_and_toc_is_a_list(tmp_path):
    from make_pdf import make_booklet_pdf

    md = convert(make_booklet_pdf(tmp_path / "cartilha.pdf"), "native").markdown
    lines = md.splitlines()
    heads = [ln for ln in lines if ln.startswith("#")]
    for sec in ("APRESENTAÇÃO", "DIREITOS", "DEVERES"):
        assert any(ln.startswith("## ") and ln.endswith(sec) for ln in heads), heads
    assert heads[0].startswith("# ") and "GUIA DO VOLUNTARIO" in heads[0]     # capa acima das seções
    assert "- Apresentação" in lines and not any(ln.strip("# ") in ("3", "4", "5") for ln in lines)
    assert "cartilha_final 1.indd" not in md
