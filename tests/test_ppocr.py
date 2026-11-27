# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 dontstopbelieve — Markinho
"""OCR PP-OCR latino: regra do modo automático, modelos locais e leitura com acentos."""
import pytest

from markinho import ocr


def _lines(n, conf, height, chars=30):
    return [{"text": "x" * chars, "conf": conf, "height": height, "chars": chars} for _ in range(n)]


def test_regra_letra_miuda_em_pagina_limpa():
    assert ocr.prefer_ppocr(_lines(20, 88, 40), 3300)            # limpa e miúda: PP-OCR
    assert not ocr.prefer_ppocr(_lines(20, 88, 110), 3300)       # letra normal: Tesseract
    assert not ocr.prefer_ppocr(_lines(20, 45, 40), 3300)        # papel velho (confiança baixa): Tesseract
    assert not ocr.prefer_ppocr(_lines(2, 90, 40), 3300)         # quase sem texto
    assert not ocr.prefer_ppocr(_lines(20, 90, 40), 0)


def test_sem_modelos_nao_oferece_o_pp_ocr(monkeypatch, tmp_path):
    monkeypatch.setenv("MARKINHO_PPOCR", str(tmp_path / "nada"))
    monkeypatch.setattr(ocr, "_bundle_dirs", lambda: [tmp_path])
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "usuario"))
    monkeypatch.setattr(ocr, "_has_module", lambda name: name != "rapidocr_onnxruntime")
    assert not ocr.ppocr_ready()
    assert "rapidocr" not in ocr.available_backends()


def test_modelos_achados_na_pasta(monkeypatch, tmp_path):
    d = tmp_path / "ppocr"
    d.mkdir()
    for name in (ocr.PPOCR_REC, ocr.PPOCR_DICT, ocr.PPOCR_DET):
        (d / name).write_bytes(b"x")
    monkeypatch.setenv("MARKINHO_PPOCR", str(d))
    assert ocr.ppocr_dir() == d and ocr._ppocr_det() == d / ocr.PPOCR_DET


def test_automatico_troca_para_pp_ocr_em_letra_miuda(monkeypatch):
    from PIL import Image

    if ocr.tesseract_cmd() is None:
        pytest.skip("sem Tesseract")
    monkeypatch.setattr(ocr, "prefer_ppocr", lambda lines, h: True)
    monkeypatch.setattr(ocr, "ppocr_ready", lambda: True)
    monkeypatch.setattr(ocr, "_tess_data", lambda img, tl, cfg: (
        {"text": ["Texto", "lido"], "conf": [90, 90], "block_num": [1, 1], "par_num": [1, 1], "line_num": [1, 1],
         "left": [0, 60], "top": [0, 0], "width": [50, 40], "height": [10, 10]}, 90.0))
    pp = [{"text": "Texto lido pelo PP-OCR", "x0": 0, "x1": 100, "top": 0, "bottom": 10, "height": 10,
           "conf": 95, "chars": 22}]
    monkeypatch.setattr(ocr, "_rapid_lines", lambda img: pp)
    img = Image.new("RGB", (200, 100), "white")
    assert ocr.ocr_lines(img, "auto", "por+eng", enhance_img=False) == pp
    # escolhendo o Tesseract à mão, não troca
    assert ocr.ocr_lines(img, "tesseract", "por+eng", enhance_img=False)[0]["text"] == "Texto lido"


def test_le_com_acentos_de_verdade():
    if not ocr.ppocr_ready():
        pytest.skip("modelos do PP-OCR não baixados (markinho --download-models ppocr)")
    from PIL import Image, ImageDraw, ImageFont

    img = Image.new("RGB", (1400, 160), "white")
    try:
        font = ImageFont.truetype("DejaVuSans.ttf", 40)
    except OSError:
        pytest.skip("sem fonte")
    ImageDraw.Draw(img).text((30, 50), "Ação, não, coração, señal, München, élève", fill="black", font=font)
    ocr.refresh()
    text = " ".join(ln["text"] for ln in ocr.ocr_lines(img, "rapidocr", "por+eng"))
    for word in ("Ação", "não", "coração", "señal", "München", "élève"):
        assert word in text, text
