# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 dontstopbelieve — Markinho
"""Colar e converter: texto formatado (página da web, Word, e-mail), texto simples ou imagem
da área de transferência → Markdown."""
from __future__ import annotations

import tempfile
from pathlib import Path


def html_to_md(html: str) -> str:
    """HTML colado (navegador, Word, Outlook) → Markdown, sem estilos do Office."""
    from .converters import html_to_markdown
    from .core import normalize

    return normalize(html_to_markdown(html))


def text_to_md(text: str) -> str:
    from .core import normalize

    return normalize(text.replace("\r\n", "\n"))


def image_to_md(image_png: bytes) -> str:
    """Imagem colada (print de tela, foto) → texto por OCR, com o mesmo tratamento das imagens."""
    from .core import convert
    from .postprocess import OutputOptions

    with tempfile.TemporaryDirectory(prefix="markinho_colar_") as tmp:
        p = Path(tmp) / "imagem_colada.png"
        p.write_bytes(image_png)
        md = convert(p, "native", {"image_embed_original": False}, None, OutputOptions(images="none")).markdown
    lines = md.splitlines()
    if lines and lines[0].startswith("# "):
        lines[0] = "# Imagem colada"
    return "\n".join(lines)


def clipboard_to_markdown(html: str | None = None, text: str | None = None,
                          image_png: bytes | None = None) -> tuple[str, str]:
    """(markdown, origem) a partir do que houver na área de transferência; prefere HTML."""
    if html and html.strip():
        md = html_to_md(html)
        if md.strip():
            return md, "texto formatado"
    if text and text.strip():
        return text_to_md(text), "texto"
    if image_png:
        return image_to_md(image_png), "imagem (OCR)"
    return "", ""
