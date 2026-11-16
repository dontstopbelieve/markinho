# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 dontstopbelieve — Markinho
"""Proteções contra arquivos maliciosos ou defeituosos (vindos de e-mail, downloads…).

* ZIP-bomba: documentos do Office, OpenDocument, EPUB e ZIP são pacotes compactados; um pacote
  pequeno pode se expandir para dezenas de GB e esgotar a memória. Conferimos o índice do pacote
  antes de abrir e lemos cada parte com limite.
* Páginas gigantes de PDF: a imagem para OCR tem um limite de pixels.
"""
from __future__ import annotations

import math
import zipfile
from pathlib import Path

MAX_TOTAL_UNCOMPRESSED = 2 * 1024 ** 3     # 2 GB somando tudo o que há no pacote
MAX_ENTRY = 512 * 1024 ** 2                # 512 MB por parte
MAX_RATIO = 250                            # expansão suspeita (texto comum fica < 20×)
MAX_ENTRIES = 50_000
MAX_PAGE_PIXELS = 40_000_000               # ~ A3 a 300 dpi; uma A4 a 300 dpi tem 8,7 milhões


class UnsafeFileError(Exception):
    """O arquivo parece malicioso ou grande demais para abrir com segurança."""


def _gb(n: int) -> str:
    return f"{n / 1024 ** 3:.1f} GB"


def check_zip(path: str | Path) -> None:
    """Recusa pacotes compactados que se expandiriam demais. Não faz nada se não for ZIP."""
    path = Path(path)
    try:
        if not zipfile.is_zipfile(path):
            return
        with zipfile.ZipFile(path) as zf:
            infos = zf.infolist()
    except (OSError, zipfile.BadZipFile):
        return                                   # o conversor mostra o erro de leitura normal
    if len(infos) > MAX_ENTRIES:
        raise UnsafeFileError(f"o pacote tem {len(infos)} arquivos internos (suspeito)")
    total = 0
    for info in infos:
        total += info.file_size
        if info.file_size > MAX_ENTRY:
            raise UnsafeFileError(f"uma parte interna teria {_gb(info.file_size)} ao descompactar")
        if info.compress_size and info.file_size > 10 * 1024 ** 2 \
                and info.file_size / info.compress_size > MAX_RATIO:
            raise UnsafeFileError("compressão anormal (possível “bomba de compressão”)")
    if total > MAX_TOTAL_UNCOMPRESSED:
        raise UnsafeFileError(f"o conteúdo descompactado teria {_gb(total)} (possível “bomba de compressão”)")


def read_zip_member(zf: zipfile.ZipFile, name, limit: int = MAX_ENTRY) -> bytes:
    """Lê uma parte do pacote sem passar de `limit` bytes, mesmo que o índice minta o tamanho."""
    with zf.open(name) as fh:
        data = fh.read(limit + 1)
    if len(data) > limit:
        raise UnsafeFileError("uma parte interna do pacote é grande demais")
    return data


def safe_resolution(width_pt: float, height_pt: float, wanted: float) -> float:
    """Resolução (dpi) para renderizar uma página sem passar de MAX_PAGE_PIXELS."""
    area = max(width_pt, 1.0) * max(height_pt, 1.0) / (72.0 * 72.0)      # polegadas²
    limit = math.sqrt(MAX_PAGE_PIXELS / area)
    return max(10.0, min(float(wanted), limit))
