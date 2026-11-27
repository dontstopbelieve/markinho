# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 dontstopbelieve — Markinho
"""Créditos: componentes incluídos (com licença) e projetos que inspiraram ideias.

Regra: componente *incluído* = biblioteca/programa que vai dentro do Markinho → crédito e texto da
licença são obrigatórios. Projeto que *inspirou* = só ideias/funcionalidades (ideias não têm direito
autoral); nenhum código deles foi copiado. Citamos por transparência e agradecimento.
"""
from __future__ import annotations

from .i18n import tr

import importlib.util
from dataclasses import dataclass


@dataclass(frozen=True)
class Credit:
    name: str
    author: str
    license: str
    url: str
    role: str
    module: str = ""        # módulo Python para saber se está nesta instalação ("" = sempre)


INCLUDED: tuple[Credit, ...] = (
    Credit(tr("Python"), tr("Python Software Foundation"), "PSF-2.0", "https://www.python.org", tr("Linguagem do programa")),
    Credit(tr("Pygments"), tr("Georg Brandl e colaboradores"), tr("BSD-2-Clause"), "https://pygments.org",
           tr("Código colorido na visualização e no HTML exportado"), "pygments"),
    Credit(tr("Raleway (fonte)"), tr("The Raleway Project Authors"), "OFL-1.1", "https://github.com/impallari/Raleway",
           tr("Letras “MD” do ícone (convertidas em desenho; a fonte não é instalada)")),
    Credit(tr("Qt / PySide6"), tr("The Qt Company e colaboradores"), "LGPL-3.0", "https://www.qt.io/qt-for-python",
           tr("Interface gráfica e visualizador de PDF"), tr("PySide6")),
    Credit("pypdf", tr("Mathieu Fenniak e colaboradores"), tr("BSD-3-Clause"), "https://github.com/py-pdf/pypdf",
           tr("Leitura de PDF"), "pypdf"),
    Credit(tr("pdfplumber / pdfminer.six"), tr("Jeremy Singer-Vine; Yusuke Shinyama e colaboradores"), "MIT",
           "https://github.com/jsvine/pdfplumber", tr("Análise de layout e tabelas em PDF"), "pdfplumber"),
    Credit(tr("pypdfium2 / PDFium"), tr("pypdfium2-team; Google/Foxit"), tr("Apache-2.0 / BSD-3-Clause"),
           "https://github.com/pypdfium2-team/pypdfium2", tr("Imagens de páginas de PDF"), "pypdfium2"),
    Credit(tr("python-docx / python-pptx"), tr("Steve Canny e colaboradores"), "MIT", "https://github.com/python-openxml",
           tr("Word e PowerPoint"), "docx"),
    Credit("openpyxl", tr("Eric Gazoni, Charlie Clark"), "MIT", "https://openpyxl.readthedocs.io", tr("Excel"), "openpyxl"),
    Credit("xlrd", tr("John Machin, Chris Withers"), "BSD", "https://github.com/python-excel/xlrd", tr("Excel 97-2003"),
           "xlrd"),
    Credit(tr("Beautiful Soup"), tr("Leonard Richardson"), "MIT", "https://www.crummy.com/software/BeautifulSoup/",
           tr("Leitura de HTML"), "bs4"),
    Credit("markdownify", tr("Matthew Tretter e colaboradores"), "MIT",
           "https://github.com/matthewwithanm/python-markdownify", tr("HTML → Markdown"), "markdownify"),
    Credit(tr("Python-Markdown"), tr("Waylan Limberg e colaboradores"), tr("BSD-3-Clause"),
           "https://github.com/Python-Markdown/markdown", tr("Markdown → HTML"), "markdown"),
    Credit("mdformat", tr("Taneli Hukkinen"), "MIT", "https://github.com/hukkin/mdformat", tr("Perfil padronizado"),
           "mdformat"),
    Credit("ftfy", tr("Robyn Speer"), tr("Apache-2.0"), "https://github.com/rspeer/python-ftfy",
           tr("Correção de codificação (mojibake)"), "ftfy"),
    Credit(tr("Pillow"), tr("Jeffrey A. Clark e colaboradores"), "MIT-CMU", "https://python-pillow.org", tr("Imagens"), "PIL"),
    Credit(tr("AnyDoc"), tr("Firecrawl"), "MIT", "https://github.com/firecrawl/anydoc",
           tr("Office antigo (.doc/.xls/.ppt), OpenDocument e RTF"), "anydoc"),
    Credit(tr("MCP Python SDK"), tr("Anthropic e colaboradores (Model Context Protocol)"), "MIT",
           "https://github.com/modelcontextprotocol/python-sdk", tr("Servidor para assistentes de IA"), "mcp"),
    Credit(tr("Pandoc"), tr("John MacFarlane e colaboradores"), tr("GPL-2.0-or-later (programa separado)"),
           "https://pandoc.org", tr("Exportação para ~20 formatos e leitura de ODT, LaTeX, RST…"), "pypandoc"),
    Credit(tr("Tesseract OCR"), tr("Ray Smith, Google e colaboradores"), tr("Apache-2.0"),
           "https://github.com/tesseract-ocr/tesseract", tr("OCR (reconhecimento de texto)"), "pytesseract"),
    Credit(tr("Docling"), tr("IBM Research / LF AI & Data"), tr("MIT (código) · Apache-2.0, CDLA-Permissive-2.0, MIT (modelos)"),
           "https://github.com/docling-project/docling", tr("IA de análise de layout"), "docling"),
    Credit(tr("PyTorch"), tr("Meta e colaboradores"), tr("BSD-3-Clause"), "https://pytorch.org", tr("Execução dos modelos de IA"),
           "torch"),
    Credit(tr("Transformers / Hugging Face Hub"), tr("Hugging Face"), tr("Apache-2.0"), "https://github.com/huggingface",
           tr("Carregamento dos modelos"), "transformers"),
    Credit(tr("MarkItDown"), tr("Microsoft"), "MIT", "https://github.com/microsoft/markitdown", tr("Motor de conversão extra"),
           "markitdown"),
    Credit(tr("RapidOCR / ONNX Runtime"), tr("RapidAI; Microsoft"), tr("Apache-2.0 / MIT"), "https://github.com/RapidAI/RapidOCR",
           tr("OCR de reserva do Docling"), "rapidocr_onnxruntime"),
)

INSPIRED_BY: tuple[Credit, ...] = (
    Credit(tr("SoMark / OXR"), tr("SoMark (Shanghai Shoukou Technology)"), "—", "https://github.com/SoMarkAI",
           tr("Ideias de uso: selo de “nada saiu do computador”, sumário clicável, texto aparecendo enquanto "
           "converte, ler imagem como tabela/código e comparar versões (nada do código ou do modelo deles)")),
    Credit("markitdown", tr("Microsoft"), "MIT", "https://github.com/microsoft/markitdown",
           tr("A ideia original: converter vários formatos para Markdown pensando em IA")),
    Credit(tr("Docling"), tr("IBM Research"), "MIT", "https://github.com/docling-project/docling",
           tr("Análise de layout, tabelas e o acervo de documentos usado nos nossos testes")),
    Credit(tr("Marker"), tr("Datalab"), "GPL-3.0", "https://github.com/datalab-to/marker",
           tr("Remoção de cabeçalhos/rodapés e modos de OCR (não incluído no Markinho)")),
    Credit(tr("Pandoc"), tr("John MacFarlane"), "GPL-2.0", "https://pandoc.org", tr("Conversão entre dezenas de formatos")),
    Credit(tr("PyMuPDF4LLM"), tr("Artifex"), "AGPL-3.0", "https://github.com/pymupdf/pymupdf4llm",
           tr("PDF → Markdown rápido em CPU (não incluído no Markinho)")),
    Credit(tr("Unstructured"), tr("Unstructured Technologies"), tr("Apache-2.0"), "https://github.com/Unstructured-IO/unstructured",
           tr("Divisão em pedaços (chunking) para RAG — implementação própria")),
    Credit(tr("AnyDoc"), tr("Firecrawl"), "MIT", "https://github.com/firecrawl/anydoc", tr("Modelo único de documento")),
    Credit("file2markdown", tr("file2markdown.ai"), "—", "https://www.file2markdown.ai",
           tr("Uso por assistentes de IA via MCP — aqui, 100% local")),
)

DISCLAIMER = (
    tr("O Markinho é um projeto independente. Não é afiliado, patrocinado nem endossado pelos projetos e "
    "empresas citados; seus nomes e marcas pertencem aos respectivos donos. Os projetos listados como "
    "inspiração contribuíram com ideias — o código do Markinho foi escrito do zero, sem copiar código "
    "deles. Os componentes incluídos são usados conforme suas licenças, cujos textos acompanham o programa.")
)


def _present(module: str) -> bool:
    if not module:
        return True
    try:
        return importlib.util.find_spec(module) is not None
    except (ImportError, ValueError):
        return False


def included_here() -> list[tuple[Credit, bool]]:
    """Componentes e se estão presentes nesta instalação (depende da edição)."""
    return [(c, _present(c.module)) for c in INCLUDED]


# --------------------------------------------------------------------------- #
# Textos completos das licenças
# --------------------------------------------------------------------------- #
_LICENSE_NAMES = ("licen", "copying", "notice", "copyright", "authors")


def _bundled_licenses_dir():
    import sys
    from pathlib import Path

    for base in (Path(getattr(sys, "_MEIPASS", "")), Path(__file__).resolve().parent.parent):
        d = base / "licenses"
        if d.is_dir():
            return d
    return None


def license_files() -> list[tuple[str, str, str]]:
    """(componente, arquivo, texto). No programa instalado vem da pasta licenses/ embutida; rodando pelo
    código-fonte, lê os arquivos de licença das bibliotecas instaladas."""
    from pathlib import Path

    out: list[tuple[str, str, str]] = []
    d = _bundled_licenses_dir()
    if d is not None:
        for f in sorted(d.rglob("*")):
            if f.is_file():
                rel = f.relative_to(d)
                comp = rel.parts[1] if rel.parts[0] == "third_party" and len(rel.parts) > 2 else rel.stem
                out.append((comp, str(rel), f.read_text(encoding="utf-8", errors="replace")))
    if any(r[1].startswith("third_party") for r in out):
        return out
    from importlib.metadata import distributions

    for dist in sorted(distributions(), key=lambda x: (x.metadata.get("Name") or "").lower()):
        for f in dist.files or []:
            name = Path(str(f)).name.lower()
            if any(k in name for k in _LICENSE_NAMES) and not name.endswith((".py", ".pyc")):
                try:
                    out.append((dist.metadata.get("Name") or "?", str(f), f.read_text(encoding="utf-8")))
                except (OSError, UnicodeDecodeError, TypeError):
                    continue
    return out
