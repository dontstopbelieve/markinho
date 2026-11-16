# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 dontstopbelieve — Markinho
"""Markinho — Conversor Markdown: documentos (PDF, DOCX, XLSX, PPTX, HTML, CSV…) para Markdown e vice-versa."""
from .core import ConversionResult, ConversionError, convert, supported_extensions

__version__ = "3.0.0"
__all__ = ["convert", "ConversionResult", "ConversionError", "supported_extensions"]
