# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 dontstopbelieve — Markinho
"""Edições do Markinho: LEVE, PADRÃO e COMPLETA.

Os instaladores são "fechados": cada um já traz os componentes da sua edição. A
edição de um instalador fica gravada em `resources/edition.txt` na hora do build.
Rodando pelo código-fonte, o Markinho informa o que estiver instalado.

O Markinho é software livre (AGPL-3.0). Os componentes incluídos têm licenças permissivas
(MIT, BSD, Apache, LGPL…; veja THIRD_PARTY_LICENSES.md).
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Edition:
    id: str
    name: str
    summary: str
    features: tuple[str, ...]


LEVE = Edition("leve", "LEVE", "O essencial, leve e rápido.", (
    "Motor nativo: PDF (títulos, tabelas, colunas, código, imagens), Word, Excel, PowerPoint, HTML, EPUB, CSV…",
    "AnyDoc: Word/Excel/PowerPoint antigos (.doc, .xls, .ppt), OpenDocument (.odt/.ods/.odp) e RTF",
    "Correção de caracteres, imagens (pasta/base64), frontmatter e perfis de saída",
    "Exportação para DOCX, PDF, HTML e TXT",
    "Pedaços para RAG/IA (JSON/JSONL) com títulos, página e origem",
    "Descrição de imagens com IA local (se o Ollama estiver instalado)",
    "Servidor MCP local: Claude Desktop, Cursor e VS Code convertem arquivos pelo Markinho (só pastas autorizadas)",
))
PADRAO = Edition("padrao", "PADRÃO", "LEVE + Pandoc + OCR.", LEVE.features + (
    "Pandoc: ~35 formatos de entrada (ODT, RTF, LaTeX, RST, Jupyter…) e 21 de exportação",
    "OCR local com Tesseract (português e inglês) para escaneados e imagens",
))
COMPLETA = Edition("completa", "COMPLETA", "Tudo: inclui a IA de layout (Docling), funcionando offline.",
                   PADRAO.features + (
    "Docling: IA de layout (ordem de leitura, tabelas complexas, fórmulas), modelos já incluídos",
    "MarkItDown (Microsoft) e RapidOCR",
))
EDITIONS = {e.id: e for e in (LEVE, PADRAO, COMPLETA)}

# o que cada edição adiciona, para a mensagem "disponível na edição X"
REQUIRES = {"pandoc": "padrao", "ocr": "padrao", "docling": "completa", "markitdown": "completa",
            "rapidocr": "completa"}


def _marker() -> Path:
    return Path(__file__).resolve().parent / "resources" / "edition.txt"


def current() -> Edition | None:
    """Edição do instalador, ou None quando roda pelo código-fonte."""
    try:
        return EDITIONS.get(_marker().read_text(encoding="utf-8").strip().lower())
    except OSError:
        return None


def label() -> str:
    ed = current()
    return ed.name if ed else "código-fonte"


def upgrade_hint(feature: str) -> str:
    """Mensagem para um recurso que não veio na edição instalada."""
    need = EDITIONS.get(REQUIRES.get(feature, ""))
    ed = current()
    if need is None or ed is None:
        return ""
    order = ["leve", "padrao", "completa"]
    if order.index(ed.id) >= order.index(need.id):
        return ""
    return f"Disponível na edição {need.name} (instale-a por cima desta; suas configurações são mantidas)."
