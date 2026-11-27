# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 dontstopbelieve — Markinho
"""Créditos: componentes incluídos (com licença) e projetos que inspiraram ideias.

Regra: componente *incluído* = biblioteca/programa que vai dentro do Markinho → crédito e texto da
licença são obrigatórios. Projeto que *inspirou* = só ideias/funcionalidades (ideias não têm direito
autoral); nenhum código deles foi copiado. Citamos por transparência e agradecimento.
"""
from __future__ import annotations

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
    Credit("Python", "Python Software Foundation", "PSF-2.0", "https://www.python.org", "Linguagem do programa"),
    Credit("Pygments", "Georg Brandl e colaboradores", "BSD-2-Clause", "https://pygments.org",
           "Código colorido na visualização e no HTML exportado", "pygments"),
    Credit("Raleway (fonte)", "The Raleway Project Authors", "OFL-1.1", "https://github.com/impallari/Raleway",
           "Letras “MD” do ícone (convertidas em desenho; a fonte não é instalada)"),
    Credit("Qt / PySide6", "The Qt Company e colaboradores", "LGPL-3.0", "https://www.qt.io/qt-for-python",
           "Interface gráfica e visualizador de PDF", "PySide6"),
    Credit("pypdf", "Mathieu Fenniak e colaboradores", "BSD-3-Clause", "https://github.com/py-pdf/pypdf",
           "Leitura de PDF", "pypdf"),
    Credit("pdfplumber / pdfminer.six", "Jeremy Singer-Vine; Yusuke Shinyama e colaboradores", "MIT",
           "https://github.com/jsvine/pdfplumber", "Análise de layout e tabelas em PDF", "pdfplumber"),
    Credit("pypdfium2 / PDFium", "pypdfium2-team; Google/Foxit", "Apache-2.0 / BSD-3-Clause",
           "https://github.com/pypdfium2-team/pypdfium2", "Imagens de páginas de PDF", "pypdfium2"),
    Credit("python-docx / python-pptx", "Steve Canny e colaboradores", "MIT", "https://github.com/python-openxml",
           "Word e PowerPoint", "docx"),
    Credit("openpyxl", "Eric Gazoni, Charlie Clark", "MIT", "https://openpyxl.readthedocs.io", "Excel", "openpyxl"),
    Credit("xlrd", "John Machin, Chris Withers", "BSD", "https://github.com/python-excel/xlrd", "Excel 97-2003",
           "xlrd"),
    Credit("Beautiful Soup", "Leonard Richardson", "MIT", "https://www.crummy.com/software/BeautifulSoup/",
           "Leitura de HTML", "bs4"),
    Credit("markdownify", "Matthew Tretter e colaboradores", "MIT",
           "https://github.com/matthewwithanm/python-markdownify", "HTML → Markdown", "markdownify"),
    Credit("Python-Markdown", "Waylan Limberg e colaboradores", "BSD-3-Clause",
           "https://github.com/Python-Markdown/markdown", "Markdown → HTML", "markdown"),
    Credit("mdformat", "Taneli Hukkinen", "MIT", "https://github.com/hukkin/mdformat", "Perfil padronizado",
           "mdformat"),
    Credit("ftfy", "Robyn Speer", "Apache-2.0", "https://github.com/rspeer/python-ftfy",
           "Correção de codificação (mojibake)", "ftfy"),
    Credit("Pillow", "Jeffrey A. Clark e colaboradores", "MIT-CMU", "https://python-pillow.org", "Imagens", "PIL"),
    Credit("AnyDoc", "Firecrawl", "MIT", "https://github.com/firecrawl/anydoc",
           "Office antigo (.doc/.xls/.ppt), OpenDocument e RTF", "anydoc"),
    Credit("MCP Python SDK", "Anthropic e colaboradores (Model Context Protocol)", "MIT",
           "https://github.com/modelcontextprotocol/python-sdk", "Servidor para assistentes de IA", "mcp"),
    Credit("Pandoc", "John MacFarlane e colaboradores", "GPL-2.0-or-later (programa separado)",
           "https://pandoc.org", "Exportação para ~20 formatos e leitura de ODT, LaTeX, RST…", "pypandoc"),
    Credit("Tesseract OCR", "Ray Smith, Google e colaboradores", "Apache-2.0",
           "https://github.com/tesseract-ocr/tesseract", "OCR (reconhecimento de texto)", "pytesseract"),
    Credit("Docling", "IBM Research / LF AI & Data", "MIT (código) · Apache-2.0, CDLA-Permissive-2.0, MIT (modelos)",
           "https://github.com/docling-project/docling", "IA de análise de layout", "docling"),
    Credit("PyTorch", "Meta e colaboradores", "BSD-3-Clause", "https://pytorch.org", "Execução dos modelos de IA",
           "torch"),
    Credit("Transformers / Hugging Face Hub", "Hugging Face", "Apache-2.0", "https://github.com/huggingface",
           "Carregamento dos modelos", "transformers"),
    Credit("MarkItDown", "Microsoft", "MIT", "https://github.com/microsoft/markitdown", "Motor de conversão extra",
           "markitdown"),
    Credit("RapidOCR / ONNX Runtime", "RapidAI; Microsoft", "Apache-2.0 / MIT", "https://github.com/RapidAI/RapidOCR",
           "OCR de reserva do Docling", "rapidocr_onnxruntime"),
)

INSPIRED_BY: tuple[Credit, ...] = (
    Credit("SoMark / OXR", "SoMark (Shanghai Shoukou Technology)", "—", "https://github.com/SoMarkAI",
           "Ideias de uso: selo de “nada saiu do computador”, sumário clicável, texto aparecendo enquanto "
           "converte, ler imagem como tabela/código e comparar versões (nada do código ou do modelo deles)"),
    Credit("markitdown", "Microsoft", "MIT", "https://github.com/microsoft/markitdown",
           "A ideia original: converter vários formatos para Markdown pensando em IA"),
    Credit("Docling", "IBM Research", "MIT", "https://github.com/docling-project/docling",
           "Análise de layout, tabelas e o acervo de documentos usado nos nossos testes"),
    Credit("Marker", "Datalab", "GPL-3.0", "https://github.com/datalab-to/marker",
           "Remoção de cabeçalhos/rodapés e modos de OCR (não incluído no Markinho)"),
    Credit("Pandoc", "John MacFarlane", "GPL-2.0", "https://pandoc.org", "Conversão entre dezenas de formatos"),
    Credit("PyMuPDF4LLM", "Artifex", "AGPL-3.0", "https://github.com/pymupdf/pymupdf4llm",
           "PDF → Markdown rápido em CPU (não incluído no Markinho)"),
    Credit("Unstructured", "Unstructured Technologies", "Apache-2.0", "https://github.com/Unstructured-IO/unstructured",
           "Divisão em pedaços (chunking) para RAG — implementação própria"),
    Credit("AnyDoc", "Firecrawl", "MIT", "https://github.com/firecrawl/anydoc", "Modelo único de documento"),
    Credit("file2markdown", "file2markdown.ai", "—", "https://www.file2markdown.ai",
           "Uso por assistentes de IA via MCP — aqui, 100% local"),
)

DISCLAIMER = (
    "O Markinho é um projeto independente. Não é afiliado, patrocinado nem endossado pelos projetos e "
    "empresas citados; seus nomes e marcas pertencem aos respectivos donos. Os projetos listados como "
    "inspiração contribuíram com ideias — o código do Markinho foi escrito do zero, sem copiar código "
    "deles. Os componentes incluídos são usados conforme suas licenças, cujos textos acompanham o programa."
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
