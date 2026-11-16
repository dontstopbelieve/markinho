# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 dontstopbelieve — Markinho
"""Gera PNG em vários tamanhos, .ico (Windows) e .icns (macOS) a partir dos SVG.

Uso:  python gera_icones.py markinho.svg markinho-16.svg pasta_saida
Requer: PySide6 (desenha o SVG) e Pillow (monta o .ico/.icns).
O tamanho 16 px usa o SVG simplificado; os demais, o SVG principal.
"""
import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from PIL import Image
from PySide6.QtCore import QBuffer, QIODevice, QRectF, Qt
from PySide6.QtGui import QGuiApplication, QImage, QPainter
from PySide6.QtSvg import QSvgRenderer

main_svg, small_svg, out = sys.argv[1], sys.argv[2], sys.argv[3]
os.makedirs(out, exist_ok=True)
app = QGuiApplication([])


def render(svg: str, size: int) -> Image.Image:
    img = QImage(size, size, QImage.Format_ARGB32)
    img.fill(Qt.transparent)
    p = QPainter(img)
    p.setRenderHint(QPainter.Antialiasing)
    QSvgRenderer(svg).render(p, QRectF(0, 0, size, size))
    p.end()
    buf = QBuffer()
    buf.open(QIODevice.WriteOnly)
    img.save(buf, "PNG")
    import io
    return Image.open(io.BytesIO(bytes(buf.data()))).convert("RGBA")


sizes = [16, 24, 32, 48, 64, 128, 256, 512, 1024]
imgs = {s: render(small_svg if s == 16 else main_svg, s) for s in sizes}
for s, im in imgs.items():
    im.save(os.path.join(out, f"markinho-{s}.png"))
# .ico com vários tamanhos (o Windows escolhe o melhor para cada lugar)
ico = [imgs[s] for s in (16, 24, 32, 48, 64, 128, 256)]
ico[-1].save(os.path.join(out, "markinho.ico"), sizes=[(i.width, i.height) for i in ico],
             append_images=ico[:-1])
imgs[1024].save(os.path.join(out, "markinho.icns"))
print("gerado em", out)
