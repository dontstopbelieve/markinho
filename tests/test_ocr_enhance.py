"""Tratamento da imagem antes do OCR: contraste, página torta, página de cabeça para baixo."""
from pathlib import Path

import pytest
from PIL import Image, ImageDraw, ImageFont

from markinho import convert
from markinho.ocr import available_backends, enhance, skew_angle

has_tesseract = "tesseract" in available_backends()
FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"


def _page(lines, size=36, fg=0, bg=255) -> Image.Image:
    font = ImageFont.truetype(FONT, size) if Path(FONT).exists() else ImageFont.load_default()
    im = Image.new("L", (1700, 120 + 70 * len(lines)), bg)
    d = ImageDraw.Draw(im)
    for i, t in enumerate(lines):
        d.text((80, 60 + 70 * i), t, fill=fg, font=font)
    return im


LINES = ["Relatório anual de gestão", "Educação, saúde e habitação",
         "Ações concluídas no período", "Informações para o conselho"]


def test_skew_angle_detects_rotation():
    page = _page(LINES)
    assert skew_angle(page) == 0.0
    tilted = page.rotate(3, resample=Image.BICUBIC, fillcolor=255)
    assert abs(skew_angle(tilted) + 3) <= 0.5      # gira -3° para endireitar


def test_enhance_keeps_size_and_grayscale():
    im = _page(LINES).convert("RGB")
    out = enhance(im)
    assert out.size == im.size and out.mode == "L"


@pytest.mark.skipif(not has_tesseract, reason="Tesseract não instalado")
def test_ocr_tilted_low_contrast_photo(tmp_path):
    # foto "ruim": cinza sobre cinza e 4° torta
    img = _page(LINES, fg=110, bg=170).rotate(4, resample=Image.BICUBIC, fillcolor=170)
    img.convert("RGB").save(tmp_path / "foto.png")
    md = convert(tmp_path / "foto.png", "native", {"image_embed_original": False}).markdown
    assert "Educação, saúde e habitação" in md and "Ações concluídas" in md


@pytest.mark.skipif(not has_tesseract, reason="Tesseract não instalado")
def test_ocr_upside_down_page(tmp_path):
    _page(LINES).rotate(180).save(tmp_path / "invertida.png")
    md = convert(tmp_path / "invertida.png", "native", {"image_embed_original": False}).markdown
    assert "Relatório anual de gestão" in md


@pytest.mark.skipif(not has_tesseract, reason="Tesseract não instalado")
def test_best_models_broken_falls_back(tmp_path, monkeypatch):
    """Pasta de modelos “best” com problema (ex.: caminho mal passado no Windows): usa os normais."""
    from markinho import ocr

    bad = tmp_path / "pasta com espaço" / "tessdata_best"
    bad.mkdir(parents=True)
    for lang in ("por", "eng"):
        (bad / f"{lang}.traineddata").write_bytes(b"isto nao e um modelo")
    monkeypatch.setenv("MARKINHO_TESSDATA_BEST", str(bad))
    ocr.tessdata_best_dir.cache_clear()
    try:
        lines = ocr.ocr_lines(_page(LINES).convert("RGB"), "tesseract", "por+eng", model="best")
    finally:
        ocr.tessdata_best_dir.cache_clear()
    assert "Relatório anual de gestão" in " ".join(ln["text"] for ln in lines)


def test_tessdata_arg_without_windows_quotes(monkeypatch):
    from markinho import ocr

    arg = ocr._tessdata_arg("/dados/pasta com espaço/tessdata_best")
    import shlex

    assert shlex.split(arg) == ["--tessdata-dir", "/dados/pasta com espaço/tessdata_best"]
