# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 dontstopbelieve — Markinho
"""Limpeza do Markdown antes de exportar (Pandoc ou nativo).

* Nada sai do computador: imagens da internet (http/https/ftp//) não são baixadas — viram link.
* HTML perigoso não passa para o arquivo gerado: <script>, <iframe>, <object>, <embed>, <form>,
  <meta>, <base>, <link>, atributos on…= e links javascript:.
* Opcionalmente (servidor MCP), imagens locais fora das pastas permitidas são removidas: o assistante
  não consegue fazer o Pandoc embutir, por exemplo, um arquivo pessoal num DOCX.

Blocos de código (``` … ```) não são alterados: ali o texto é exibido, não executado.
"""
from __future__ import annotations

from .i18n import tr

import re
from pathlib import Path

_REMOTE = re.compile(r"^(?:[a-z][a-z0-9+.-]*:)?//|^(?:https?|ftp|file):", re.I)
_MD_IMG = re.compile(r"!\[([^\]]*)\]\(\s*<?([^)\s>]+)>?((?:\s+\"[^\"]*\")?)\s*\)")
_DANGEROUS = ("script", "style", "iframe", "object", "embed", "form", "noscript", "template")
_OPEN_DANGEROUS = re.compile(r"<(" + "|".join(_DANGEROUS) + r")\b", re.I)
_DANGEROUS_TAG = re.compile(r"</?(?:script|iframe|object|embed|form|meta|base|link|noscript|template|frame|frameset)"
                            r"\b[^>]*>", re.I)
_TAG = re.compile(r"<[a-zA-Z][^<>]*>")
_ON_ATTR = re.compile(r"(?<=[\s\"'/])on[a-zA-Z]+\s*=\s*(?:\"[^\"]*\"|'[^']*'|[^\s>]+)")
_JS_URL = re.compile(r"(?<![\w-])((?:href|src|action|formaction|xlink:href)\s*=\s*[\"']?)\s*"
                     r"(?:javascript|vbscript|data:text/html)", re.I)
_SRC = re.compile(r"(?<![\w-])src\s*=\s*(?:\"([^\"]*)\"|'([^']*)'|([^\s>]+))", re.I)


def _drop_blocks(text: str) -> str:
    """Remove <script>…</script> (e afins) sem regex com retrocesso: procura o fechamento com find."""
    low = text.lower()
    out, pos = [], 0
    unclosed: set[str] = set()          # tag sem fechamento até o fim: não procura de novo (evita O(n²))
    while True:
        m = _OPEN_DANGEROUS.search(text, pos)
        if not m:
            out.append(text[pos:])
            return "".join(out)
        out.append(text[pos:m.start()])
        name = m.group(1).lower()
        close = -1 if name in unclosed else low.find("</" + name, m.end())
        if close < 0:
            unclosed.add(name)
        if close < 0:                                   # sem fechamento: corta só a tag de abertura
            gt = text.find(">", m.end())
            pos = len(text) if gt < 0 else gt + 1
            continue
        gt = text.find(">", close)
        pos = len(text) if gt < 0 else gt + 1


def _outside(src: str, base_dir: Path | None, allowed: list[Path]) -> bool:
    if src.startswith("data:"):
        return False
    p = Path(src.split("#")[0].split("?")[0]).expanduser()
    if not p.is_absolute():
        p = (base_dir or Path.cwd()) / p
    try:
        p = p.resolve()
    except OSError:
        return True
    return not any(p == f or p.is_relative_to(f) for f in allowed)


def _clean_text(text: str, base_dir: Path | None, allowed: list[Path] | None, notes: set[str]) -> str:
    def md_img(m: re.Match) -> str:
        alt, src = m.group(1), m.group(2)
        if _REMOTE.match(src):
            notes.add(tr("imagens da internet viraram links (nada é baixado)"))
            return f"[{alt or 'imagem'}]({src})"
        if allowed is not None and _outside(src, base_dir, allowed):
            notes.add(tr("imagens fora das pastas permitidas foram removidas"))
            return f"*[{alt or 'imagem'}]*"
        return m.group(0)

    def clean_tag(m: re.Match) -> str:
        tag = _ON_ATTR.sub("", m.group(0))
        tag = _JS_URL.sub(r"\1#", tag)
        if tag[:4].lower() == "<img":
            sm = _SRC.search(tag)
            src = next((g for g in sm.groups() if g is not None), "") if sm else ""
            if src and _REMOTE.match(src):
                notes.add(tr("imagens da internet viraram links (nada é baixado)"))
                return f'<a href="{src}">[imagem]</a>'
            if src and allowed is not None and _outside(src, base_dir, allowed):
                notes.add(tr("imagens fora das pastas permitidas foram removidas"))
                return "[imagem]"
        return tag

    before = text
    text = _drop_blocks(text)
    text = _DANGEROUS_TAG.sub("", text)
    cleaned = _TAG.sub(clean_tag, text)
    if cleaned != text or text != before:
        if _ON_ATTR.search(text) or _JS_URL.search(text) or text != before:
            notes.add("HTML ativo (scripts, eventos) foi removido")
    text = _MD_IMG.sub(md_img, cleaned)
    return text


def sanitize_markdown(md: str, base_dir: str | Path | None = None,
                      allowed_dirs: list[Path] | None = None) -> tuple[str, list[str]]:
    """(markdown limpo, avisos). Fora dos blocos de código."""
    base = Path(base_dir).resolve() if base_dir else None
    allowed = [Path(a).resolve() for a in allowed_dirs] if allowed_dirs is not None else None
    notes: set[str] = set()
    out, buf, in_code, fence = [], [], False, ""
    for line in md.splitlines(keepends=True):
        stripped = line.lstrip()
        if not in_code and (stripped.startswith("```") or stripped.startswith("~~~")):
            out.append(_clean_text("".join(buf), base, allowed, notes))
            buf, in_code, fence = [], True, stripped[:3]
            out.append(line)
        elif in_code:
            out.append(line)
            if stripped.startswith(fence):
                in_code = False
        else:
            buf.append(line)
    out.append(_clean_text("".join(buf), base, allowed, notes))
    return "".join(out), sorted(notes)
