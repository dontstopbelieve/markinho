# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 dontstopbelieve — Markinho
"""Modelos de IA para uso 100% offline (Docling e Marker).

Docling e Marker baixam redes neurais na primeira execução. Para usar sem internet:

1. Num computador com internet: `markinho --download-models docling` (ou pelo botão
   "Baixar modelos" na janela Motores).
2. Os modelos ficam em `models_dir()`. Para levar a outro computador, copie essa pasta
   para o mesmo local, ou para uma pasta `models/` ao lado do executável do Markinho
   (modo portátil), ou aponte a variável de ambiente `MARKINHO_MODELS` para ela.
"""
from __future__ import annotations

from .i18n import tr

import os
import sys
from pathlib import Path


def user_data_dir() -> Path:
    if sys.platform == "win32":
        base = Path(os.environ.get("LOCALAPPDATA") or Path.home() / "AppData" / "Local")
        return base / "Markinho"
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / "Markinho"
    return Path(os.environ.get("XDG_DATA_HOME") or Path.home() / ".local" / "share") / "markinho"


def bundled_models_dir() -> Path | None:
    """Modelos que vêm junto do programa (edição COMPLETA ou modo portátil): somente leitura."""
    env = os.environ.get("MARKINHO_MODELS")
    if env:
        return Path(env)
    if getattr(sys, "frozen", False):
        portable = Path(sys.executable).parent / "models"
        if portable.is_dir():
            return portable
    return None


def models_dir() -> Path:
    """Pasta gravável onde o Markinho baixa modelos (sempre na pasta do usuário)."""
    return user_data_dir() / "models"


def docling_artifacts() -> Path | None:
    """Pasta com os modelos do Docling (embutidos, baixados ou de pacotes extras), se houver."""
    from .packs import merged_docling_dir

    return merged_docling_dir()


def setup_environment() -> None:
    """Faz as bibliotecas de IA guardarem/procurarem modelos na pasta do Markinho."""
    root = models_dir()
    os.environ.setdefault("HF_HOME", str(root / "huggingface"))     # Docling, EasyOCR via HF Hub
    os.environ.setdefault("MODEL_CACHE_DIR", str(root / "datalab"))  # Marker / Surya
    os.environ.setdefault("EASYOCR_MODULE_PATH", str(root / "easyocr"))


def status() -> dict[str, str]:
    out = {}
    for name, sub in (("docling", "docling"), ("marker", "datalab")):
        p = (docling_artifacts() or models_dir() / sub) if name == "docling" else models_dir() / sub
        if p.is_dir() and any(p.rglob("*")):
            size = sum(f.stat().st_size for f in p.rglob("*") if f.is_file())
            out[name] = tr('baixados ({0:.0f} MB) em {1}').format(size / 1e6, p)
        else:
            out[name] = tr("não baixados")
    return out


def download_models(which: str, progress=print) -> Path:
    """Baixa os modelos de 'docling' ou 'marker' para a pasta local."""
    setup_environment()
    root = models_dir()
    if which == "docling":
        target = root / "docling"
        target.mkdir(parents=True, exist_ok=True)
        progress(tr('Baixando modelos do Docling para {0} …').format(target))
        try:
            from docling.utils.model_downloader import download_models as dl
        except ImportError as exc:
            raise RuntimeError(tr("Docling não está instalado (pip install docling).")) from exc
        try:
            dl(output_dir=target, progress=False, with_easyocr=True)
        except TypeError:   # versões com assinatura diferente
            dl(output_dir=target)
        progress(tr("Modelos do Docling prontos."))
        return target
    if which == "marker":
        target = root / "datalab"
        target.mkdir(parents=True, exist_ok=True)
        progress(tr('Baixando modelos do Marker para {0} …').format(target))
        try:
            from marker.models import create_model_dict
        except ImportError as exc:
            raise RuntimeError(tr("Marker não está instalado (pip install marker-pdf).")) from exc
        create_model_dict()
        progress(tr("Modelos do Marker prontos."))
        return target
    raise ValueError(tr('Modelo desconhecido: {0}').format(which))
