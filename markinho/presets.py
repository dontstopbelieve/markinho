# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 dontstopbelieve — Markinho
"""Modos de conversão: desempenho × qualidade.

* **Rápido**       – motor nativo sem OCR, sem análise de layout do PDF e sem extrair imagens.
                     Frações de segundo por documento; ideal para lotes grandes de arquivos digitais.
* **Equilibrado**  – padrão: motor automático, layout do PDF, colunas, imagens e OCR só nas páginas
                     escaneadas.
* **Qualidade**    – Docling (IA de layout) com tabelas no modo preciso, fórmulas e código, quando
                     estiver instalado (edição COMPLETA); sem ele, o motor nativo com OCR em todas as
                     páginas do PDF. Bem mais lento, sobretudo sem placa de vídeo.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class Preset:
    id: str
    label: str
    description: str
    engine: str                                   # "auto" ou id do motor
    engine_options: dict[str, dict[str, Any]] = field(default_factory=dict)   # por motor
    images: str | None = None                     # None = não muda a opção de imagens


PRESETS: dict[str, Preset] = {p.id: p for p in (
    Preset("rapido", "Rápido", "Sem OCR, sem análise de layout e sem imagens: em PDFs sai texto corrido, sem títulos. "
           "Para lotes grandes de arquivos digitais.",
           "auto",
           {"native": {"ocr": "off", "pdf_layout": False, "pdf_columns": False, "pdf_strip_headers": True,
                       "tables_html": True}},
           images="none"),
    Preset("equilibrado", "Equilibrado (padrão)", "Layout do PDF, colunas, imagens e OCR só onde não há texto.",
           "auto",
           {"native": {"ocr": "auto", "pdf_layout": True, "pdf_columns": True, "pdf_strip_headers": True,
                       "tables_html": True}},
           images="folder"),
    Preset("qualidade", "Máxima qualidade", "IA de layout (Docling) com tabelas precisas, fórmulas e código. "
           "Sem o Docling, OCR mais preciso nas páginas escaneadas. Mais lento.",
           "docling",
           {"docling": {"ocr": True, "tables": True, "table_accurate": True, "formulas": True, "code": True},
            # sem o Docling: OCR só nas páginas sem texto, com os modelos mais precisos. Forçar OCR em PDF
            # digital piora o resultado (perde tamanhos de fonte, títulos e negrito).
            "native": {"ocr": "auto", "ocr_model": "best", "pdf_layout": True, "pdf_columns": True, "pdf_strip_headers": True,
                       "tables_html": True}},
           images="folder"),
)}


def resolve(preset_id: str) -> tuple[str, dict[str, dict[str, Any]], str | None]:
    """(motor, opções por motor, modo das imagens) do modo, considerando o que está instalado."""
    from .engines import ENGINES

    p = PRESETS[preset_id]
    engine = p.engine
    if engine != "auto" and not ENGINES[engine].available()[0]:
        engine = "native"          # Qualidade sem Docling: motor nativo com OCR forçado
    return engine, p.engine_options, p.images


def engine_for(preset_id: str, path) -> tuple[str, dict[str, Any]]:
    """Motor e opções para um arquivo: no modo Qualidade, formatos que o Docling não lê usam o automático."""
    from pathlib import Path

    from .engines import ENGINES, pick_engine

    engine, opts, _ = resolve(preset_id)
    if engine != "auto" and not ENGINES[engine].supports(Path(path)):
        engine = pick_engine(Path(path)).id
    return engine, dict(opts.get(engine, {}))
