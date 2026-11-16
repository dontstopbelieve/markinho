# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 dontstopbelieve — Markinho
from fontTools.ttLib import TTFont
from fontTools.varLib import instancer
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
from fontTools.pens.boundsPen import BoundsPen
import sys
H = float(sys.argv[1]) if len(sys.argv) > 1 else 104
f = instancer.instantiateVariableFont(TTFont(sys.argv[2] if len(sys.argv) > 2 else "Raleway.ttf"), {"wght": 800})
gs = f.getGlyphSet(); cmap = f.getBestCmap()
placed, x = [], 0
for c in "MD":
    n = cmap[ord(c)]; placed.append((n, x)); x += gs[n].width - 10
bp = BoundsPen(gs)
for n, dx in placed: gs[n].draw(TransformPen(bp, (1, 0, 0, 1, dx, 0)))
xmin, ymin, xmax, ymax = bp.bounds
s = H / (ymax - ymin); w = (xmax - xmin) * s
cx, cy = 256, 258
tx = cx - w / 2 - xmin * s; ty = cy + H / 2 + ymin * s
d = []
for n, dx in placed:
    pen = SVGPathPen(gs); gs[n].draw(TransformPen(pen, (s, 0, 0, -s, tx + dx * s, ty))); d.append(pen.getCommands())
md = " ".join(d)
G, Y = "#1DBF4E", "#FFDF00"
svg = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512" width="512" height="512">
  <title>Markinho</title>
  <defs>
    <linearGradient id="fundo" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="#0B3A94"/>
      <stop offset="1" stop-color="#002776"/>
    </linearGradient>
  </defs>
  <!-- fundo: azul da bandeira do Brasil; fora do quadrado arredondado é transparente -->
  <rect x="8" y="8" width="496" height="496" rx="112" fill="url(#fundo)"/>
  <!-- seta verde: base da folha e sobe pela esquerda -->
  <path d="M336 432 H140 A32 32 0 0 1 108 400 V160" fill="none" stroke="{G}"
        stroke-width="42" stroke-linecap="round" stroke-linejoin="round"/>
  <path d="M108 54 L58 156 H158 Z" fill="{G}" stroke="{G}" stroke-width="10" stroke-linejoin="round"/>
  <!-- seta amarela: topo, canto dobrado e desce pela direita -->
  <path d="M180 86 H334 L404 156 V354" fill="none" stroke="{Y}"
        stroke-width="42" stroke-linecap="round" stroke-linejoin="round"/>
  <path d="M404 460 L354 358 H454 Z" fill="{Y}" stroke="{Y}" stroke-width="10" stroke-linejoin="round"/>
  <!-- MD na fonte Raleway ExtraBold (SIL OFL 1.1), convertida em curvas -->
  <path fill="#FFFFFF" d="{md}"/>
</svg>
'''
open("markinho.svg", "w").write(svg)
s16 = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512" width="16" height="16">
  <title>Markinho (16 px)</title>
  <!-- versão para 16 px: linhas grossas, sem letras -->
  <rect x="0" y="0" width="512" height="512" rx="96" fill="#002776"/>
  <path d="M318 432 H130 A34 34 0 0 1 96 398 V196" fill="none" stroke="{G}"
        stroke-width="72" stroke-linecap="round" stroke-linejoin="round"/>
  <path d="M96 40 L18 196 H174 Z" fill="{G}"/>
  <path d="M206 84 H326 L416 174 V316" fill="none" stroke="{Y}"
        stroke-width="72" stroke-linecap="round" stroke-linejoin="round"/>
  <path d="M416 472 L338 316 H494 Z" fill="{Y}"/>
</svg>
'''
open("markinho-16.svg", "w").write(s16)
print("MD largura", round(w), "de", round(cx - w/2), "a", round(cx + w/2))
