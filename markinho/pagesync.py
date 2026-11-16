# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 dontstopbelieve — Markinho
"""Leitura acompanhada: liga uma posição do texto convertido à página do original (e vice-versa).

A conversão guarda, para cada página, o começo do primeiro trecho de texto dela. Aqui procuramos
esses trechos no texto exibido (Markdown ou visualização), já com correções e perfil aplicados, por
isso a busca usa só as primeiras palavras, sem marcação de Markdown.
"""
from __future__ import annotations

import bisect
import re

_MD = re.compile(r"[#*_`>\[\]()!|~-]+")


def _key(text: str, words: int = 6) -> str:
    plain = _MD.sub(" ", text)
    return " ".join(plain.split()[:words])


def page_positions(page_starts: list[tuple[int, str]], shown: str) -> list[tuple[int, int]]:
    """[(posição no texto exibido, página)] em ordem; páginas cujo trecho não foi achado ficam de fora."""
    out: list[tuple[int, int]] = []
    flat = " ".join(_MD.sub(" ", shown).split())
    # mapa de posição no texto “achatado” → posição no texto exibido
    idx_map: list[int] = []
    prev_space = True
    for i, ch in enumerate(_MD.sub(lambda m: " " * len(m.group(0)), shown)):
        if ch.isspace():
            if not prev_space:
                idx_map.append(i)
            prev_space = True
        else:
            idx_map.append(i)
            prev_space = False
    start = 0
    for page, snippet in page_starts:
        key = _key(snippet)
        if not key:
            continue
        pos = flat.find(key, start)
        if pos < 0:
            continue
        out.append((idx_map[pos] if pos < len(idx_map) else len(shown), page))
        start = pos + 1
    return out


def page_at(positions: list[tuple[int, int]], pos: int) -> int | None:
    if not positions:
        return None
    i = bisect.bisect_right([p for p, _ in positions], pos) - 1
    return positions[max(i, 0)][1]


def position_of(positions: list[tuple[int, int]], page: int) -> int | None:
    for p, pg in positions:
        if pg >= page:
            return p
    return None
