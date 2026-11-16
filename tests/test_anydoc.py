"""Motor AnyDoc: formatos antigos do Office, OpenDocument e RTF — sempre local."""
from pathlib import Path

import pytest

from markinho import convert
from markinho.engines import ENGINES, pick_engine
from markinho.postprocess import OutputOptions

FX = Path(__file__).parent / "fixtures"
pytestmark = pytest.mark.skipif(not ENGINES["anydoc"].available()[0], reason="AnyDoc não instalado")


@pytest.mark.parametrize("name", ["antigo.doc", "antigo.odt", "antigo.rtf"])
def test_word_like(name):
    r = convert(FX / name)
    assert r.engine == "anydoc"
    md = r.markdown
    assert "Relatório Antigo" in md and "**negrito**" in md
    assert "- item um\n- item dois" in md and "| 2024 | R$ 10 |" in md
    assert "****" not in md                       # pedaços de mesmo estilo foram unidos
    assert len(r.assets) == 1                     # a imagem embutida virou ativo


def test_spreadsheets_merged_cells():
    xls = convert(FX / "planilha.xls").markdown   # .xls: leitor nativo, agora com mesclagens
    ods = convert(FX / "planilha.ods").markdown   # .ods: AnyDoc
    for md in (xls, ods):
        assert '<td colspan="2">Total mesclado</td>' in md and "<td>Café</td>" in md


@pytest.mark.parametrize("name", ["slides.ppt", "slides.odp"])
def test_presentations_with_notes(name):
    md = convert(FX / name).markdown
    assert "Apresentação Antiga" in md and "Ponto principal" in md and "Nota do apresentador" in md
    assert "<number>" not in md and "\n> *\n" not in md   # marcadores vazios removidos


def test_auto_engine_choice():
    for name in ("antigo.doc", "antigo.odt", "antigo.rtf", "slides.ppt", "planilha.ods"):
        assert pick_engine(FX / name).id == "anydoc"
    assert pick_engine(FX / "planilha.xls").id == "native"


def test_images_none_mode():
    r = convert(FX / "antigo.doc", output=OutputOptions(images="none"))
    assert not r.assets and "![" not in r.markdown


def test_never_uses_network(monkeypatch):
    """O modo de OCR hospedado (que envia o arquivo à Firecrawl) nunca pode ser acionado."""
    import anydoc
    import urllib.request

    def boom(*a, **k):
        raise AssertionError("acesso à rede!")

    monkeypatch.setattr(urllib.request, "urlopen", boom)
    monkeypatch.setattr(anydoc, "_parse_hosted", boom, raising=False)
    for name in ("antigo.doc", "antigo.rtf", "slides.ppt", "planilha.ods"):
        convert(FX / name, "anydoc")


def test_scanned_pdf_message(tmp_path):
    reportlab = pytest.importorskip("reportlab")  # noqa: F841
    import sys

    sys.path.insert(0, str(Path(__file__).parent))
    from make_pdf import make_scanned_pdf

    from markinho import ConversionError

    with pytest.raises(ConversionError, match="OCR"):
        convert(make_scanned_pdf(tmp_path / "s.pdf"), "anydoc")
