# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 dontstopbelieve — Markinho
"""Edições do Markinho: PADRÃO e COMPLETA.

Até 27/11/2026 havia também a LEVE (sem OCR nem Pandoc); ela foi juntada à PADRÃO. Um marcador antigo
“leve” é lido como PADRÃO.

Os instaladores são "fechados": cada um já traz os componentes da sua edição. A
edição de um instalador fica gravada em `resources/edition.txt` na hora do build.
Rodando pelo código-fonte, o Markinho informa o que estiver instalado.

O Markinho é software livre (AGPL-3.0). Os componentes incluídos têm licenças permissivas
(MIT, BSD, Apache, LGPL…; veja THIRD_PARTY_LICENSES.md).
"""
from __future__ import annotations

from .i18n import tr

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Edition:
    id: str
    name: str
    summary: str
    features: tuple[str, ...]


_BASE = (
    tr("Motor nativo: PDF (títulos, tabelas, colunas, código, imagens), Word, Excel, PowerPoint, HTML, EPUB, CSV…"),
    tr("AnyDoc: Word/Excel/PowerPoint antigos (.doc, .xls, .ppt), OpenDocument (.odt/.ods/.odp) e RTF"),
    tr("Correção de caracteres, imagens (pasta/base64), frontmatter e perfis de saída"),
    tr("Exportação para DOCX, PDF, HTML e TXT"),
    tr("Pedaços para RAG/IA (JSON/JSONL) com títulos, página e origem"),
    tr("Descrição de imagens com IA local (se o Ollama estiver instalado)"),
    tr("Servidor MCP local: Claude Desktop, Cursor e VS Code convertem arquivos pelo Markinho (só pastas autorizadas)"),
    tr("Pandoc: ~35 formatos de entrada (ODT, RTF, LaTeX, RST, Jupyter…) e 21 de exportação"),
    tr("OCR local com Tesseract (português e inglês) para escaneados e imagens"),
)
PADRAO = Edition("padrao", "PADRÃO", tr("Tudo para o dia a dia, inclusive escaneados (OCR) e 21 formatos de exportação."),
                 _BASE)
COMPLETA = Edition("completa", "COMPLETA", tr("Tudo: inclui a IA de layout (Docling), funcionando offline."),
                   PADRAO.features + (
    tr("Docling: IA de layout (ordem de leitura, tabelas complexas, fórmulas), modelos já incluídos"),
    tr("MarkItDown (Microsoft) e RapidOCR"),
))
EDITIONS = {e.id: e for e in (PADRAO, COMPLETA)}
_ALIASES = {"leve": "padrao"}          # edição antiga, juntada à PADRÃO

# o que cada edição adiciona, para a mensagem "disponível na edição X"
REQUIRES = {"pandoc": "padrao", "ocr": "padrao", "docling": "completa", "markitdown": "completa",
            "rapidocr": "completa"}


def _marker() -> Path:
    return Path(__file__).resolve().parent / "resources" / "edition.txt"


def current() -> Edition | None:
    """Edição do instalador, ou None quando roda pelo código-fonte."""
    try:
        mark = _marker().read_text(encoding="utf-8").strip().lower()
        return EDITIONS.get(_ALIASES.get(mark, mark))
    except OSError:
        return None


def label() -> str:
    ed = current()
    return ed.name if ed else tr("código-fonte")


def upgrade_hint(feature: str) -> str:
    """Mensagem para um recurso que não veio na edição instalada."""
    need = EDITIONS.get(REQUIRES.get(feature, ""))
    ed = current()
    if need is None or ed is None:
        return ""
    order = ["padrao", "completa"]
    if order.index(ed.id) >= order.index(need.id):
        return ""
    return tr('Disponível na edição {0} (instale-a por cima desta; suas configurações são mantidas).').format(need.name)
