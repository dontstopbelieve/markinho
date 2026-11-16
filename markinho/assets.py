# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 dontstopbelieve — Markinho
"""Imagens e outros ativos extraídos dos documentos.

As imagens ficam guardadas em memória (`AssetSink.files`) e o Markdown aponta para
caminhos relativos como `relatorio_assets/imagem_001.png`. Na hora de salvar, a
pasta é gravada ao lado do `.md`. O modo de saída decide como elas aparecem:

* "folder" – link relativo para a pasta `<nome>_assets/` (padrão);
* "base64" – imagem embutida no próprio Markdown (arquivo único e portátil);
* "none"   – remove as imagens (mantém a descrição como texto, se houver).
"""
from __future__ import annotations

import base64
import html
import mimetypes
import re
from pathlib import Path
from typing import Sequence

IMAGE_MODES = [("folder", "Pasta <nome>_assets/ ao lado do .md"),
               ("base64", "Embutidas no .md (base64)"),
               ("none", "Não incluir imagens")]

_IMG_RE = re.compile(r"!\[([^\]]*)\]\(\s*<?([^)\s>]+)>?(?:\s+\"[^\"]*\")?\s*\)")
_DATA_RE = re.compile(r"^data:(image/[\w.+-]+);base64,(.+)$", re.S)


def safe_stem(stem: str) -> str:
    s = re.sub(r"[^\w.-]+", "_", stem, flags=re.UNICODE).strip("._")
    return s[:60] or "documento"


_IMAGE_EXTS = {".png", ".jpg", ".gif", ".bmp", ".tiff", ".webp", ".svg", ".emf", ".wmf", ".ico"}


class AssetSink:
    """Recebe imagens durante a conversão e devolve a referência Markdown."""

    def __init__(self, stem: str, enabled: bool = True):
        self.folder = f"{safe_stem(stem)}_assets"
        self.files: dict[str, bytes] = {}
        self.enabled = enabled
        self._n = 0

    def add(self, data: bytes, ext: str = ".png", alt: str = "") -> str:
        """Guarda a imagem e devolve `![alt](pasta/imagem_NNN.ext)` (ou "" se desligado)."""
        if not self.enabled or not data:
            return ""
        ext = ext if ext.startswith(".") else "." + ext
        ext = {".jpeg": ".jpg", ".jpe": ".jpg", ".tif": ".tiff"}.get(ext.lower(), ext.lower())
        if ext not in _IMAGE_EXTS:          # nome vindo do documento: nunca gravar .exe, .bat…
            ext = ".png"
        # mesma imagem repetida (ex.: logotipo) reaproveita o arquivo
        for name, blob in self.files.items():
            if blob == data:
                return f"![{_alt(alt)}]({name})"
        self._n += 1
        name = f"{self.folder}/imagem_{self._n:03d}{ext}"
        self.files[name] = data
        return f"![{_alt(alt)}]({name})"

    def add_pil(self, img, alt: str = "") -> str:
        import io

        buf = io.BytesIO()
        fmt = "PNG"
        if getattr(img, "mode", "") in ("CMYK",):
            img = img.convert("RGB")
        img.save(buf, fmt)
        return self.add(buf.getvalue(), ".png", alt)


def _alt(text: str) -> str:
    return re.sub(r"[\[\]\n]+", " ", text or "").strip()


# --------------------------------------------------------------------------- #
# Normalização das imagens produzidas por qualquer motor
# --------------------------------------------------------------------------- #
def absorb_images(md: str, sink: AssetSink, base_dirs: Sequence[Path] = ()) -> str:
    """Transforma imagens embutidas (data URI) e arquivos locais em ativos do `sink`.

    Assim, a saída de Docling, Marker, Pandoc, MarkItDown etc. passa a se comportar
    como a do motor nativo, e o usuário escolhe pasta/base64/nenhuma do mesmo jeito.
    """
    def repl(m: re.Match) -> str:
        alt, src = m.group(1), m.group(2)
        if src in sink.files:
            return m.group(0)
        dm = _DATA_RE.match(src)
        if dm:
            try:
                data = base64.b64decode(dm.group(2))
            except ValueError:
                return m.group(0)
            ext = mimetypes.guess_extension(dm.group(1)) or ".png"
            return sink.add(data, ext, alt) or m.group(0)
        if re.match(r"^[a-z]+://", src, re.I):
            return m.group(0)
        for base in [Path("."), *base_dirs]:
            p = Path(src) if Path(src).is_absolute() else Path(base) / src
            try:
                if p.is_file() and p.stat().st_size < 50_000_000:
                    return sink.add(p.read_bytes(), p.suffix or ".png", alt) or m.group(0)
            except OSError:
                continue
        return m.group(0)

    return _IMG_RE.sub(repl, md)


def render_images(md: str, files: dict[str, bytes], mode: str) -> str:
    """Aplica o modo de saída às referências de imagem conhecidas."""
    if mode == "folder" or (mode == "base64" and not files):
        return md

    def repl(m: re.Match) -> str:
        alt, src = m.group(1), m.group(2)
        if mode == "none":
            return f"*[Imagem: {alt}]*" if alt and not alt.lower().startswith("imagem") else ""
        if src not in files:
            return m.group(0)
        mime = mimetypes.guess_type(src)[0] or "image/png"
        return f"![{alt}](data:{mime};base64,{base64.b64encode(files[src]).decode()})"

    return _IMG_RE.sub(repl, md)


def referenced_assets(md: str, files: dict[str, bytes]) -> dict[str, bytes]:
    refs = {m.group(2) for m in _IMG_RE.finditer(md)}
    embeds = set(re.findall(r"!\[\[([^\]|]+)", md))          # formato Obsidian ![[arquivo.png]]
    return {k: v for k, v in files.items() if k in refs or Path(k).name in embeds}


def write_assets(md: str, files: dict[str, bytes], target_dir: Path) -> int:
    """Grava as imagens referenciadas por `md` em `target_dir`. Devolve quantas."""
    n = 0
    for rel, data in referenced_assets(md, files).items():
        dest = Path(target_dir) / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(data)
        n += 1
    return n


def set_alt_texts(md: str, alts: dict[str, str]) -> str:
    """Troca o texto alternativo das imagens (ex.: descrições geradas por IA)."""
    def repl(m: re.Match) -> str:
        src = m.group(2)
        if src in alts and alts[src]:
            return f"![{_alt(alts[src])}]({src})"
        return m.group(0)

    return _IMG_RE.sub(repl, md)


def image_refs(md: str) -> list[tuple[str, str]]:
    return [(m.group(1), m.group(2)) for m in _IMG_RE.finditer(md)]


# --------------------------------------------------------------------------- #
# Tabelas com células mescladas -> HTML
# --------------------------------------------------------------------------- #
def html_table(rows: list[list[tuple[str, int, int]]], header: bool = True) -> str:
    """rows: lista de linhas; cada célula = (texto, rowspan, colspan). Células cobertas
    por uma mesclagem não aparecem na lista (como no HTML)."""
    out = ["<table>"]
    for i, row in enumerate(rows):
        tag = "th" if header and i == 0 else "td"
        cells = []
        for text, rs, cs in row:
            attrs = (f' rowspan="{rs}"' if rs > 1 else "") + (f' colspan="{cs}"' if cs > 1 else "")
            body = html.escape((text or "").strip()).replace("\n", "<br>")
            cells.append(f"<{tag}{attrs}>{body}</{tag}>")
        out.append("  <tr>" + "".join(cells) + "</tr>")
    out.append("</table>")
    return "\n".join(out)


def has_merges(rows: list[list[tuple[str, int, int]]]) -> bool:
    return any(rs > 1 or cs > 1 for row in rows for _, rs, cs in row)


def spans_from_grid(grid: list[list[str | None]], merges: list[tuple[int, int, int, int]]) -> list[list[tuple[str, int, int]]]:
    """Monta as linhas com rowspan/colspan a partir de uma grade e de uma lista de
    mesclagens (linha0, col0, linha1, col1), índices base 0 e inclusivos."""
    covered: set[tuple[int, int]] = set()
    origin: dict[tuple[int, int], tuple[int, int]] = {}
    for r0, c0, r1, c1 in merges:
        origin[(r0, c0)] = (r1 - r0 + 1, c1 - c0 + 1)
        for r in range(r0, r1 + 1):
            for c in range(c0, c1 + 1):
                if (r, c) != (r0, c0):
                    covered.add((r, c))
    rows = []
    for r, line in enumerate(grid):
        row = []
        for c, val in enumerate(line):
            if (r, c) in covered:
                continue
            rs, cs = origin.get((r, c), (1, 1))
            row.append(("" if val is None else str(val), rs, cs))
        rows.append(row)
    return rows
