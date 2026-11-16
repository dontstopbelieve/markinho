# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 dontstopbelieve — Markinho
"""Motores de conversão para Markdown.

* **Nativo**      – conversores próprios do Markinho (rápido, leve, sem IA; OCR opcional).
* **Pandoc**      – conversor universal; ótimo para DOCX, ODT, EPUB, LaTeX, RST, RTF…
* **Docling**     – IBM/LF AI; IA de layout: ordem de leitura, tabelas, fórmulas, OCR.
* **Marker**      – Datalab; PDF de alta precisão com OCR (Surya), equações e tabelas.
* **MarkItDown**  – Microsoft; rápido e amplo para formatos Office e HTML.
* **PyMuPDF4LLM** – Artifex; PDF → Markdown muito rápido em CPU (licença AGPL).

Os motores opcionais são detectados em tempo de execução: o Markinho só oferece o
que pode ser usado.
"""
from __future__ import annotations

import importlib.util
import re
import shutil
import subprocess
import sys
import threading
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any


@dataclass
class Option:
    key: str
    label: str
    kind: str              # "bool", "choice", "text", "int"
    default: Any
    choices: list[tuple[str, str]] = field(default_factory=list)  # (valor, rótulo)
    help: str = ""


class Engine:
    id = ""
    name = ""
    description = ""
    install_hint = ""
    license = ""
    heavy = False          # usa modelos de IA (roda um arquivo por vez)
    options: list[Option] = []

    def available(self) -> tuple[bool, str]:
        return True, ""

    def extensions(self) -> set[str]:
        return set()

    def supports(self, path: Path) -> bool:
        return path.suffix.lower() in self.extensions()

    def convert(self, path: Path, opts: dict[str, Any]) -> str:
        raise NotImplementedError

    def defaults(self) -> dict[str, Any]:
        return {o.key: o.default for o in self.options}


def _has(module: str) -> bool:
    try:
        return importlib.util.find_spec(module) is not None
    except (ImportError, ValueError):
        return False


def _subprocess_flags() -> dict:
    """No Windows, evita abrir uma janela de console a cada chamada ao Pandoc."""
    if sys.platform == "win32":
        return {"creationflags": 0x08000000}   # CREATE_NO_WINDOW
    return {}


# --------------------------------------------------------------------------- #
# Nativo
# --------------------------------------------------------------------------- #
class NativeEngine(Engine):
    id = "native"
    name = "Nativo"
    description = ("Conversores próprios: rápidos, leves e sem IA. Detecta títulos, tabelas, colunas e "
                   "código em PDFs, extrai imagens e faz OCR local de páginas escaneadas e imagens.")
    license = "MIT"
    options = [
        Option("ocr", "OCR (texto em imagens/escaneados)", "choice", "auto",
               [("auto", "Automático: só páginas sem texto"), ("force", "Forçar em todas as páginas"),
                ("off", "Desligado")],
               help="“Forçar” refaz o texto por OCR — útil quando o texto embutido no PDF vem com "
                    "caracteres trocados."),
        Option("ocr_backend", "Motor de OCR", "choice", "auto",
               [("auto", "Automático"), ("tesseract", "Tesseract (mantém acentos)"),
                ("rapidocr", "RapidOCR (sem instalação, perde acentos)")]),
        Option("ocr_lang", "Idiomas do OCR (Tesseract)", "text", "por+eng", help="Instalados: por (português) e eng (inglês)."),
        Option("ocr_enhance", "OCR: melhorar a imagem antes", "bool", True,
               help="Tons de cinza, contraste automático, endireita páginas tortas e gira páginas de lado. "
                    "Ajuda em fotos de celular e cópias escuras ou tortas."),
        Option("ocr_model", "OCR: modelo do Tesseract", "choice", "fast",
               [("fast", "Rápido (fast)"), ("best", "Mais preciso (best), mais lento")],
               help="“Mais preciso” usa os modelos best quando instalados (Windows PADRÃO/COMPLETA); "
                    "sem eles, usa os normais."),
        Option("pdf_layout", "PDF: análise de layout (títulos, tabelas)", "bool", True),
        Option("pdf_columns", "PDF: detectar várias colunas", "bool", True,
               help="Lê cada coluna inteira antes de passar para a próxima (artigos, jornais)."),
        Option("pdf_strip_headers", "PDF: remover cabeçalhos/rodapés repetidos", "bool", True),
        Option("pdf_strip_stamps", "PDF: remover carimbos de assinatura eletrônica (PJe, SEI…)", "bool", True,
               help="Tira a faixa vertical “Assinado eletronicamente por…”, códigos verificadores e endereços de "
                    "conferência que se repetem nas margens de cada página."),
        Option("pdf_margin_top", "PDF: ignorar topo da página (%)", "int", 0,
               help="Corta uma faixa fixa no topo de todas as páginas (0 = não cortar)."),
        Option("pdf_margin_bottom", "PDF: ignorar rodapé da página (%)", "int", 0),
        Option("pdf_page_markers", "PDF: marcar início de cada página", "bool", False),
        Option("tables_html", "Tabelas mescladas viram HTML", "bool", True,
               help="Tabelas com células mescladas (rowspan/colspan) são gravadas em HTML, que o "
                    "Markdown aceita; sem isso, as células são repetidas numa tabela simples."),
        Option("pages", "Páginas (ex.: 1-3,5)", "text", "", help="Vazio = todas. Vale para PDF."),
    ]

    def extensions(self) -> set[str]:
        from .core import supported_extensions

        return set(supported_extensions())

    def convert(self, path: Path, opts: dict[str, Any]) -> str:
        from .core import convert_native

        return convert_native(path, opts)


# --------------------------------------------------------------------------- #
# Pandoc
# --------------------------------------------------------------------------- #
PANDOC_READERS = {
    ".docx": "docx", ".odt": "odt", ".epub": "epub", ".html": "html", ".htm": "html",
    ".xhtml": "html", ".rtf": "rtf", ".tex": "latex", ".latex": "latex", ".rst": "rst",
    ".org": "org", ".textile": "textile", ".wiki": "mediawiki", ".mediawiki": "mediawiki",
    ".dbk": "docbook", ".docbook": "docbook", ".ipynb": "ipynb", ".fb2": "fb2",
    ".opml": "opml", ".csv": "csv", ".tsv": "tsv", ".typ": "typst", ".pptx": "pptx",
    ".xlsx": "xlsx", ".adoc": "asciidoc", ".asciidoc": "asciidoc", ".djot": "djot",
    ".bib": "bibtex", ".md": "markdown", ".markdown": "markdown", ".t2t": "t2t",
    ".muse": "muse", ".jira": "jira", ".pod": "pod", ".man": "man", ".1": "man",
}

MD_FLAVORS = [
    ("gfm", "GitHub (GFM)"),
    ("commonmark_x", "CommonMark + extensões"),
    ("markdown", "Pandoc Markdown"),
    ("markdown_strict", "Markdown original (estrito)"),
    ("markdown_mmd", "MultiMarkdown"),
]


@lru_cache(maxsize=1)
def pandoc_path() -> str | None:
    try:
        import pypandoc

        p = pypandoc.get_pandoc_path()
        if p:
            return p
    except Exception:  # noqa: BLE001
        pass
    return shutil.which("pandoc")


@lru_cache(maxsize=4)
def pandoc_formats(kind: str) -> frozenset[str]:
    exe = pandoc_path()
    if not exe:
        return frozenset()
    flag = "--list-input-formats" if kind == "in" else "--list-output-formats"
    try:
        out = subprocess.run([exe, flag], capture_output=True, text=True, timeout=20, **_subprocess_flags()).stdout
    except (OSError, subprocess.SubprocessError):
        return frozenset()
    return frozenset(out.split())


@lru_cache(maxsize=1)
def pandoc_version() -> str:
    exe = pandoc_path()
    if not exe:
        return ""
    try:
        out = subprocess.run([exe, "--version"], capture_output=True, text=True, timeout=20,
                             **_subprocess_flags()).stdout
        return out.split("\n", 1)[0].replace("pandoc", "").strip()
    except (OSError, subprocess.SubprocessError):
        return ""


def run_pandoc(args: list[str], input_text: str | None = None, timeout: int = 300) -> str:
    exe = pandoc_path()
    if not exe:
        raise RuntimeError("Pandoc não encontrado.")
    proc = subprocess.run([exe, *args], input=input_text, capture_output=True, text=True,
                          encoding="utf-8", timeout=timeout, **_subprocess_flags())
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip() or f"pandoc saiu com código {proc.returncode}")
    return proc.stdout


class PandocEngine(Engine):
    id = "pandoc"
    name = "Pandoc"
    description = ("Conversor universal de documentos. Excelente para DOCX, ODT, EPUB, LaTeX, RST, RTF, "
                   "Jupyter e dezenas de outros formatos. Não lê PDF.")
    install_hint = "pip install pypandoc_binary   (já inclui o Pandoc)"
    license = "GPL-2.0 (programa separado)"
    options = [
        Option("flavor", "Dialeto Markdown", "choice", "gfm", MD_FLAVORS),
        Option("wrap", "Quebra de linha", "choice", "none",
               [("none", "Não quebrar"), ("auto", "Quebrar em 72 colunas"), ("preserve", "Preservar original")]),
        Option("toc", "Gerar sumário", "bool", False),
    ]

    def available(self) -> tuple[bool, str]:
        if pandoc_path():
            return True, f"Pandoc {pandoc_version()}"
        from .edition import upgrade_hint

        return False, upgrade_hint("pandoc") or "Pandoc não encontrado."

    def extensions(self) -> set[str]:
        fmts = pandoc_formats("in")
        return {ext for ext, fmt in PANDOC_READERS.items() if fmt in fmts}

    def convert(self, path: Path, opts: dict[str, Any]) -> str:
        reader = PANDOC_READERS[path.suffix.lower()]
        flavor = opts.get("flavor", "gfm")
        args = [str(path), "-f", reader, "-t", flavor, f"--wrap={opts.get('wrap', 'none')}"]
        if opts.get("toc"):
            args += ["--toc", "-s"]
        if opts.get("_extract_images") and opts.get("_tmpdir"):
            # as imagens vão para uma pasta temporária; o núcleo as transforma em ativos
            args.append(f"--extract-media={opts['_tmpdir']}")
        return run_pandoc(args)


# --------------------------------------------------------------------------- #
# Docling
# --------------------------------------------------------------------------- #
class DoclingEngine(Engine):
    id = "docling"
    name = "Docling"
    description = ("IA de análise de layout (IBM / LF AI & Data). Ordem de leitura, tabelas complexas, "
                   "fórmulas, código e OCR para PDFs escaneados e imagens. Mais lento; baixa modelos na 1ª vez.")
    install_hint = "pip install docling"
    license = "MIT"
    heavy = True
    options = [
        Option("ocr", "OCR (texto em imagens/escaneados)", "bool", True),
        Option("force_ocr", "Forçar OCR em todas as páginas", "bool", False,
               help="Ignora o texto embutido no PDF e reconhece tudo por OCR — útil quando o "
                    "texto do PDF tem caracteres trocados."),
        Option("ocr_lang", "Idiomas do OCR (EasyOCR)", "text", "pt,en",
               help="Códigos separados por vírgula. Só vale quando o OCR do Docling é o EasyOCR."),
        Option("tables", "Estrutura de tabelas (TableFormer)", "bool", True),
        Option("table_accurate", "Tabelas: modo preciso", "bool", True),
        Option("formulas", "Reconhecer fórmulas (LaTeX)", "bool", False),
        Option("code", "Reconhecer blocos de código", "bool", False),
    ]
    _cache: dict[tuple, Any] = {}
    _lock = threading.Lock()

    FALLBACK_EXTS = {".pdf", ".docx", ".pptx", ".xlsx", ".html", ".htm", ".xhtml", ".md", ".csv", ".png",
                     ".jpg", ".jpeg", ".tif", ".tiff", ".bmp", ".webp", ".adoc", ".asciidoc"}

    def available(self) -> tuple[bool, str]:
        if _has("docling"):
            try:
                from importlib.metadata import version

                return True, f"Docling {version('docling')}"
            except Exception:  # noqa: BLE001
                return True, "Docling instalado"
        from .edition import upgrade_hint

        return False, upgrade_hint("docling") or "Docling não está instalado."

    _exts: set[str] | None = None

    def extensions(self) -> set[str]:
        """Extensões lidas da versão instalada do Docling (cada versão aceita formatos novos).

        Importar o Docling leva segundos; por isso a lista exata só é lida quando ele já
        foi carregado (após a 1ª conversão). Antes disso, vale uma lista conservadora."""
        if DoclingEngine._exts is None and "docling.datamodel.base_models" in sys.modules:
            try:
                from docling.datamodel.base_models import FormatToExtensions

                DoclingEngine._exts = {"." + e.lower().lstrip(".") for lst in FormatToExtensions.values()
                                       for e in lst} or None
            except Exception:  # noqa: BLE001
                pass
        return DoclingEngine._exts or set(self.FALLBACK_EXTS)

    def _converter(self, opts: dict[str, Any]):
        from docling.datamodel.base_models import InputFormat
        from docling.datamodel.pipeline_options import PdfPipelineOptions, TableFormerMode
        from docling.document_converter import DocumentConverter, ImageFormatOption, PdfFormatOption

        key = tuple(sorted((k, str(v)) for k, v in opts.items() if not k.startswith("_tmp")))
        with self._lock:
            if key in self._cache:
                return self._cache[key]
            po = PdfPipelineOptions()
            from .models import docling_artifacts

            local = docling_artifacts()
            if local is not None:
                po.artifacts_path = str(local)      # modelos embutidos ou baixados antes: funciona offline
                # com os modelos no computador, nenhuma biblioteca de IA tenta acessar a internet
                import os as _os

                _os.environ["HF_HUB_OFFLINE"] = "1"
                _os.environ["TRANSFORMERS_OFFLINE"] = "1"
            if hasattr(po, "enable_remote_services"):
                po.enable_remote_services = False   # nunca usar serviços remotos (APIs de IA na nuvem)
            po.do_ocr = bool(opts.get("ocr", True))
            po.do_table_structure = bool(opts.get("tables", True))
            if po.do_table_structure:
                po.table_structure_options.mode = (
                    TableFormerMode.ACCURATE if opts.get("table_accurate", True) else TableFormerMode.FAST)
            po.do_formula_enrichment = bool(opts.get("formulas"))
            po.do_code_enrichment = bool(opts.get("code"))
            if opts.get("_extract_images"):
                po.generate_picture_images = True
                po.images_scale = 2.0
            # OCR: o mesmo Tesseract do Markinho (mantém acentos e não baixa modelos extras);
            # sem Tesseract, fica o OCR padrão do Docling (RapidOCR/EasyOCR)
            from .ocr import tesseract_cmd, tesseract_languages

            cmd = tesseract_cmd()
            if cmd and po.do_ocr:
                try:
                    from docling.datamodel.pipeline_options import TesseractCliOcrOptions

                    have = set(tesseract_languages())
                    langs = [x for x in ("por", "eng") if x in have] or ["eng"]
                    po.ocr_options = TesseractCliOcrOptions(lang=langs, tesseract_cmd=cmd)
                except Exception:  # noqa: BLE001  - versão do Docling sem essa opção
                    pass
            if hasattr(po.ocr_options, "force_full_page_ocr"):
                po.ocr_options.force_full_page_ocr = bool(opts.get("force_ocr"))
            langs = [x.strip() for x in str(opts.get("ocr_lang", "")).split(",") if x.strip()]
            if langs and type(po.ocr_options).__name__ == "EasyOcrOptions":
                po.ocr_options.lang = langs
            conv = DocumentConverter(format_options={
                InputFormat.PDF: PdfFormatOption(pipeline_options=po),
                InputFormat.IMAGE: ImageFormatOption(pipeline_options=po),
            })
            self._cache.clear()
            self._cache[key] = conv
            return conv

    def convert(self, path: Path, opts: dict[str, Any]) -> str:
        result = self._converter(opts).convert(str(path))
        doc = result.document
        try:
            from docling_core.types.doc import ImageRefMode

            mode = ImageRefMode.EMBEDDED if opts.get("_extract_images") else ImageRefMode.PLACEHOLDER
            return doc.export_to_markdown(image_mode=mode)
        except Exception:  # noqa: BLE001
            return doc.export_to_markdown()


# --------------------------------------------------------------------------- #
# Marker
# --------------------------------------------------------------------------- #
class MarkerEngine(Engine):
    id = "marker"
    name = "Marker"
    description = ("PDF → Markdown de alta precisão (Datalab). OCR com Surya, equações em LaTeX, "
                   "tabelas, remoção de cabeçalhos/rodapés. Melhor com GPU; baixa modelos na 1ª vez.")
    install_hint = "pip install marker-pdf      (outros formatos: pip install marker-pdf[full])"
    license = "GPL-3.0 (código) + licença própria dos modelos"
    heavy = True
    options = [
        Option("force_ocr", "Forçar OCR em todas as páginas", "bool", False,
               help="Refaz todo o texto por OCR. Use quando o texto do PDF vem com caracteres trocados."),
        Option("disable_ocr", "Desativar OCR (só texto embutido)", "bool", False),
        Option("strip_existing_ocr", "Descartar OCR antigo do PDF e refazer", "bool", False),
        Option("paginate_output", "Separar páginas no resultado", "bool", False),
        Option("keep_headers_footers", "Manter cabeçalhos e rodapés", "bool", False),
        Option("page_range", "Páginas (ex.: 0,5-10)", "text", "", help="Numeração começa em 0."),
        Option("use_llm", "Melhorar com LLM", "bool", False,
               help="Usa um LLM para tabelas e matemática. Para ficar 100% local, configure o "
                    "Ollama conforme a documentação do Marker."),
    ]
    _models = None
    _lock = threading.Lock()

    EXTS_PDF = {".pdf", ".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp", ".webp", ".gif"}
    EXTS_FULL = {".docx", ".pptx", ".xlsx", ".html", ".htm", ".epub", ".odt", ".ods", ".odp"}

    def available(self) -> tuple[bool, str]:
        if _has("marker"):
            return True, "Marker instalado"
        return False, "Marker não está instalado (não incluído no Markinho: os modelos têm restrição de uso comercial)."

    def extensions(self) -> set[str]:
        return self.EXTS_PDF | self.EXTS_FULL

    def convert(self, path: Path, opts: dict[str, Any]) -> str:
        from marker.converters.pdf import PdfConverter
        from marker.models import create_model_dict
        from marker.output import text_from_rendered

        with self._lock:
            if MarkerEngine._models is None:
                MarkerEngine._models = create_model_dict()
        config: dict[str, Any] = {"output_format": "markdown"}
        for key in ("force_ocr", "disable_ocr", "strip_existing_ocr", "paginate_output",
                    "keep_headers_footers", "use_llm"):
            if opts.get(key):
                config[key] = True
        if not opts.get("_extract_images"):
            config["disable_image_extraction"] = True
        if str(opts.get("page_range", "")).strip():
            config["page_range"] = str(opts["page_range"]).strip()
        try:
            from marker.config.parser import ConfigParser

            parser = ConfigParser(config)
            converter = PdfConverter(config=parser.generate_config_dict(), artifact_dict=MarkerEngine._models,
                                     processor_list=parser.get_processors(), renderer=parser.get_renderer(),
                                     llm_service=parser.get_llm_service() if config.get("use_llm") else None)
        except Exception:  # noqa: BLE001  - API mais simples (versões antigas/novas)
            converter = PdfConverter(artifact_dict=MarkerEngine._models, config=config)
        rendered = converter(str(path))
        text, _, images = text_from_rendered(rendered)
        tmp = opts.get("_tmpdir")
        if images and tmp:
            # o Marker devolve as imagens à parte (nome -> PIL); grava para o núcleo absorver
            for name, img in images.items():
                try:
                    img.save(Path(tmp) / name)
                except Exception:  # noqa: BLE001
                    pass
        return text


# --------------------------------------------------------------------------- #
# MarkItDown (Microsoft)
# --------------------------------------------------------------------------- #
class MarkItDownEngine(Engine):
    id = "markitdown"
    name = "MarkItDown"
    description = ("Conversor da Microsoft, rápido e com suporte amplo a Office (DOCX, XLSX, PPTX), HTML, "
                   "PDF simples, Outlook (.msg), EPUB, CSV, JSON, XML e ZIP. Sem IA.")
    install_hint = "pip install markitdown[all]"
    license = "MIT"
    EXTS = {".docx", ".xlsx", ".xls", ".pptx", ".pdf", ".html", ".htm", ".csv", ".json", ".xml", ".zip",
            ".epub", ".msg", ".ipynb", ".txt", ".md", ".rss", ".atom"}

    def available(self) -> tuple[bool, str]:
        if _has("markitdown"):
            try:
                from importlib.metadata import version

                return True, f"MarkItDown {version('markitdown')}"
            except Exception:  # noqa: BLE001
                return True, "MarkItDown instalado"
        from .edition import upgrade_hint

        return False, upgrade_hint("markitdown") or "MarkItDown não está instalado."

    def extensions(self) -> set[str]:
        return self.EXTS

    def convert(self, path: Path, opts: dict[str, Any]) -> str:
        from markitdown import MarkItDown

        md = MarkItDown(enable_plugins=False)
        try:
            result = md.convert(str(path), keep_data_uris=bool(opts.get("_extract_images")))
        except TypeError:   # versões sem keep_data_uris
            result = md.convert(str(path))
        return result.text_content or ""


# --------------------------------------------------------------------------- #
# PyMuPDF4LLM (Artifex)
# --------------------------------------------------------------------------- #
class PyMuPDF4LLMEngine(Engine):
    id = "pymupdf4llm"
    name = "PyMuPDF4LLM"
    description = ("PDF → Markdown muito rápido em CPU, sem modelos pesados: títulos por fonte, tabelas, "
                   "colunas e imagens. Atenção: licença AGPL-3.0 (uso comercial fechado exige licença).")
    install_hint = "pip install pymupdf4llm"
    license = "AGPL-3.0"
    options = [
        Option("pages", "Páginas (ex.: 1-3,5)", "text", ""),
        Option("page_chunks_markers", "Marcar início de cada página", "bool", False),
    ]
    EXTS = {".pdf", ".xps", ".epub", ".mobi", ".fb2", ".cbz", ".svg"}

    def available(self) -> tuple[bool, str]:
        if _has("pymupdf4llm"):
            return True, "PyMuPDF4LLM instalado"
        return False, "PyMuPDF4LLM não está instalado (não incluído no Markinho: licença AGPL)."

    def extensions(self) -> set[str]:
        return self.EXTS

    def convert(self, path: Path, opts: dict[str, Any]) -> str:
        import pymupdf4llm

        kwargs: dict[str, Any] = {"show_progress": False}
        spec = str(opts.get("pages", "")).strip()
        if spec:
            import pymupdf

            from .pdf import parse_pages

            with pymupdf.open(str(path)) as doc:
                kwargs["pages"] = parse_pages(spec, doc.page_count)
        if opts.get("_extract_images") and opts.get("_tmpdir"):
            kwargs.update(write_images=True, image_path=opts["_tmpdir"])
        import contextlib
        import io

        with contextlib.redirect_stdout(io.StringIO()):   # a biblioteca imprime diagnósticos
            if opts.get("page_chunks_markers"):
                chunks = pymupdf4llm.to_markdown(str(path), page_chunks=True, **kwargs)
                return "\n\n".join(f"<!-- Página {c['metadata'].get('page', i + 1)} -->\n\n{c['text']}"
                                   for i, c in enumerate(chunks))
            return pymupdf4llm.to_markdown(str(path), **kwargs)


# --------------------------------------------------------------------------- #
# AnyDoc (Firecrawl)
# --------------------------------------------------------------------------- #
class AnyDocEngine(Engine):
    id = "anydoc"
    name = "AnyDoc"
    description = ("Conversor em Rust (Firecrawl), muito rápido. Lê Word/Excel/PowerPoint antigos (.doc, .xls, "
                   ".ppt), OpenDocument (.odt/.ods/.odp), RTF, EPUB, além de DOCX/XLSX/PPTX e PDF com texto. "
                   "Notas de rodapé, equações e notas do apresentador. 100% local (o OCR hospedado nunca é usado).")
    install_hint = "pip install firecrawl-anydoc"
    license = "MIT"
    options = [
        Option("tables_html", "Tabelas mescladas viram HTML", "bool", True),
    ]

    def available(self) -> tuple[bool, str]:
        if _has("anydoc"):
            from .anydoc_engine import version

            return True, f"AnyDoc {version()}".strip()
        return False, "AnyDoc não está instalado."

    def extensions(self) -> set[str]:
        from .anydoc_engine import EXTENSIONS

        return set(EXTENSIONS)

    def convert(self, path: Path, opts: dict[str, Any]) -> str:
        from .anydoc_engine import convert
        from .core import current_sink

        try:
            return convert(path, opts, current_sink())
        except Exception as exc:  # noqa: BLE001
            if type(exc).__name__ == "NeedsOcrError":
                raise RuntimeError("o PDF não tem texto (é escaneado). Use o motor Nativo, que faz OCR local, "
                                   "ou o Docling.") from exc
            if type(exc).__name__ == "EncryptedError":
                raise RuntimeError("o arquivo está protegido por senha.") from exc
            raise


# --------------------------------------------------------------------------- #
# Registro
# --------------------------------------------------------------------------- #
ENGINES: dict[str, Engine] = {e.id: e for e in (
    NativeEngine(), AnyDocEngine(), PandocEngine(), DoclingEngine(), MarkerEngine(), MarkItDownEngine(),
    PyMuPDF4LLMEngine())}

AUTO = "auto"
# ordem de preferência do modo automático (sem IA por padrão: é mais rápido)
_AUTO_ORDER = ["native", "anydoc", "pandoc", "markitdown", "docling", "marker", "pymupdf4llm"]
# formatos que o motor nativo não lê: o AnyDoc (rápido, leve) vem primeiro; sem ele, o Pandoc
_ANYDOC_FIRST = {".doc", ".docm", ".dot", ".dotx", ".ppt", ".pps", ".pot", ".pptm", ".ppsx", ".ppsm",
                 ".xlsb", ".odt", ".ods", ".odp", ".rtf"}
_AUTO_PREFER = {".tex": "pandoc", ".latex": "pandoc", ".ipynb": "pandoc", ".msg": "markitdown",
                **{e: "anydoc" for e in _ANYDOC_FIRST}}
_IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp", ".webp", ".gif"}


def get_engine(engine_id: str) -> Engine:
    return ENGINES[engine_id]


def available_engines() -> list[Engine]:
    return [e for e in ENGINES.values() if e.available()[0]]


def pick_engine(path: Path, engine_id: str = AUTO) -> Engine:
    """Escolhe o motor para o arquivo. Em modo automático, usa o melhor disponível que suporta a extensão."""
    ext = path.suffix.lower()
    if engine_id != AUTO:
        eng = ENGINES[engine_id]
        ok, why = eng.available()
        if not ok:
            raise RuntimeError(f"{eng.name}: {why} Instale com: {eng.install_hint}")
        if not eng.supports(path):
            raise RuntimeError(f"O motor {eng.name} não aceita arquivos '{ext}'.")
        return eng
    order = list(_AUTO_ORDER)
    pref = _AUTO_PREFER.get(ext)
    if ext in _IMAGE_EXTS:
        from .ocr import available_backends

        # imagem: OCR leve se houver; senão, Docling (que traz OCR próprio)
        pref = "native" if available_backends() else "docling"
    if pref:
        order.remove(pref)
        order.insert(0, pref)
    for eid in order:
        eng = ENGINES[eid]
        if eng.available()[0] and eng.supports(path):
            return eng
    raise RuntimeError(f"Nenhum motor disponível converte arquivos '{ext or path.name}'.")


def all_input_extensions() -> list[str]:
    exts: set[str] = set()
    for e in available_engines():
        exts |= e.extensions()
    return sorted(exts)


def safe_filename(name: str) -> str:
    return re.sub(r'[<>:"/\\|?*\x00-\x1f]+', "_", name).strip() or "documento"
