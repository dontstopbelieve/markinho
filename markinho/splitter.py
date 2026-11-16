# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 dontstopbelieve — Markinho
"""Dividir um Markdown longo em vários arquivos, um por título (capítulo/seção)."""
from __future__ import annotations


def split_by_headings(md: str, level: int = 1) -> list[tuple[str, str]]:
    """[(título, texto)] cortando nos títulos de nível ≤ `level` (fora de blocos de código).
    O que vier antes do primeiro título fica numa parte “Início”."""
    parts: list[tuple[str, list[str]]] = []
    title, buf = "Início", []
    in_code = False
    for line in md.splitlines():
        s = line.lstrip()
        if s.startswith("```") or s.startswith("~~~"):
            in_code = not in_code
        if not in_code and s.startswith("#"):
            hashes = len(s) - len(s.lstrip("#"))
            if 1 <= hashes <= level and s[hashes:hashes + 1] in (" ", "\t"):
                if any(x.strip() for x in buf):
                    parts.append((title, buf))
                title, buf = s[hashes:].strip().rstrip("#").strip() or "Sem título", [line]
                continue
        buf.append(line)
    if any(x.strip() for x in buf):
        parts.append((title, buf))
    return [(t, "\n".join(b).strip() + "\n") for t, b in parts]
