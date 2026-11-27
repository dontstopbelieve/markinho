# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 dontstopbelieve — Markinho
"""“Copiar para IA”: texto enxuto (perfil IA), estimativa de tokens e divisão em partes que cabem
no limite do assistente (ChatGPT, Claude, Gemini…). Tudo local: nada é enviado a lugar nenhum."""
from __future__ import annotations

from .i18n import tr

import math

CHARS_PER_TOKEN = 3.6       # português costuma gastar um pouco mais de tokens que o inglês (≈4)

# limites de referência (tokens). O limite real depende do plano e do modelo de cada assistente.
LIMITS = [(tr("Sem divisão"), 0), ("8 mil tokens (conversas curtas)", 8_000), ("32 mil tokens", 32_000),
          ("100 mil tokens", 100_000), ("200 mil tokens", 200_000)]


def estimate_tokens(text: str) -> int:
    return math.ceil(len(text) / CHARS_PER_TOKEN) if text else 0


def prepare(md: str) -> str:
    """Texto para IA: sem imagens, comentários e marcações desnecessárias (perfil “llm”)."""
    import re

    from .assets import _IMG_RE
    from .postprocess import apply_profile

    # a IA não vê os arquivos de imagem: fica só a descrição (texto alternativo), quando houver
    md = _IMG_RE.sub(lambda m: f"[imagem: {m.group(1)}]" if m.group(1).strip() else "", md)
    md = re.sub(r"!\[\[[^\]]*\]\]", "", md)            # imagens no formato do Obsidian
    return apply_profile(md, "llm").strip() + "\n"


def split_for_ai(md: str, max_tokens: int) -> list[str]:
    """Divide em partes de até `max_tokens`, cortando nos títulos; cada parte diz “Parte k de n”."""
    if max_tokens <= 0 or estimate_tokens(md) <= max_tokens:
        return [md]
    from .chunker import chunk_markdown

    budget = int(max_tokens * CHARS_PER_TOKEN * 0.92)           # folga para o cabeçalho da parte
    chunks = chunk_markdown(md, max_chars=max(500, budget), overlap=0, strategy="title",
                            include_headings=True)
    parts: list[str] = []
    cur = ""
    for c in chunks:
        piece = c.text.strip()
        if cur and len(cur) + len(piece) + 2 > budget:
            parts.append(cur)
            cur = piece
        else:
            cur = f"{cur}\n\n{piece}" if cur else piece
    if cur:
        parts.append(cur)
    n = len(parts)
    if n == 1:
        return parts
    return [tr('[Parte {0} de {1}. Aguarde todas as partes antes de responder.]\n\n{2}').format(k, n, p) if k < n
            else tr('[Parte {0} de {1} — última parte.]\n\n{2}').format(k, n, p) for k, p in enumerate(parts, 1)]
