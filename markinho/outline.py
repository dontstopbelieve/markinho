# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 dontstopbelieve — Markinho
"""Sumário: títulos do Markdown (para o painel clicável e a comparação de versões)."""
from __future__ import annotations

import re

_HEAD = re.compile(r"^(#{1,6})[ \t]+(\S[^\n]{0,300})$")
_FENCE = re.compile(r"^[ \t]{0,3}(```|~~~)")


def headings(md: str) -> list[tuple[int, str, int]]:
    """[(nível 1–6, título, número da linha começando em 0)], ignorando blocos de código e o frontmatter."""
    out: list[tuple[int, str, int]] = []
    in_code = False
    lines = md.split("\n")
    start = 0
    if lines and lines[0].strip() == "---":                 # frontmatter YAML
        for k in range(1, min(len(lines), 200)):
            if lines[k].strip() == "---":
                start = k + 1
                break
    for i in range(start, len(lines)):
        line = lines[i]
        if _FENCE.match(line):
            in_code = not in_code
            continue
        if in_code:
            continue
        m = _HEAD.match(line.rstrip())
        if m:
            title = m.group(2).rstrip("#").strip()
            title = re.sub(r"[*_`]", "", title)
            if title:
                out.append((len(m.group(1)), title, i))
    return out
