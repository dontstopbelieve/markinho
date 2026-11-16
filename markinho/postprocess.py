# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 dontstopbelieve — Markinho
"""Etapas finais: metadados (frontmatter YAML) e perfis de saída (dialetos)."""
from __future__ import annotations

import datetime as dt
import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .assets import IMAGE_MODES, render_images

PROFILES = [
    ("gfm", "GitHub (GFM) — padrão"),
    ("mdformat", "Padronizado (mdformat, CommonMark + tabelas)"),
    ("obsidian", "Obsidian (frontmatter + imagens ![[...]])"),
    ("llm", "Texto para IA (sem imagens nem comentários)"),
]


@dataclass
class OutputOptions:
    """Opções de saída, iguais para qualquer motor."""
    images: str = "folder"            # folder | base64 | none
    frontmatter: bool = False
    profile: str = "gfm"
    describe_images: bool = False     # texto alternativo gerado por IA local (Ollama)
    ollama_model: str = ""
    ollama_url: str = "http://localhost:11434"
    anon: Any = None                  # anonymize.AnonOptions (None = não anonimizar)
    extra: dict[str, Any] = field(default_factory=dict)

    LABELS = {"images": IMAGE_MODES, "profile": PROFILES}


# --------------------------------------------------------------------------- #
# Metadados
# --------------------------------------------------------------------------- #
def _iso(value) -> str | None:
    if value is None:
        return None
    if isinstance(value, dt.datetime):
        return value.replace(microsecond=0).isoformat()
    s = str(value).strip()
    m = re.match(r"D:(\d{4})(\d{2})?(\d{2})?(\d{2})?(\d{2})?(\d{2})?", s)   # datas de PDF
    if m:
        parts = [p or "01" for p in m.groups()]
        return f"{parts[0]}-{parts[1]}-{parts[2]}T{m.group(4) or '00'}:{m.group(5) or '00'}:{m.group(6) or '00'}"
    return s or None


def extract_metadata(path: Path) -> dict[str, Any]:
    """Título, autor, assunto, palavras-chave, datas e nº de páginas do arquivo original."""
    meta: dict[str, Any] = {}
    ext = path.suffix.lower()
    try:
        if ext == ".pdf":
            from pypdf import PdfReader

            r = PdfReader(str(path))
            info = r.metadata or {}
            meta = {"title": info.get("/Title"), "author": info.get("/Author"), "subject": info.get("/Subject"),
                    "keywords": info.get("/Keywords"), "created": _iso(info.get("/CreationDate")),
                    "modified": _iso(info.get("/ModDate")), "pages": len(r.pages)}
        elif ext in (".docx", ".pptx", ".xlsx", ".xlsm"):
            if ext == ".docx":
                import docx

                cp = docx.Document(str(path)).core_properties
            elif ext == ".pptx":
                from pptx import Presentation

                prs = Presentation(str(path))
                cp = prs.core_properties
                meta["slides"] = len(prs.slides)
            else:
                from openpyxl import load_workbook

                wb = load_workbook(str(path), read_only=True)
                cp = wb.properties
                meta["sheets"] = len(wb.sheetnames)
                wb.close()
            meta.update({"title": cp.title, "author": getattr(cp, "author", None) or getattr(cp, "creator", None),
                         "subject": cp.subject, "keywords": cp.keywords,
                         "created": _iso(cp.created), "modified": _iso(cp.modified)})
    except Exception:  # noqa: BLE001  - metadados são um extra: nunca devem quebrar a conversão
        pass
    junk = {"(anonymous)", "(unspecified)", "anonymous", "unspecified", "unknown", "untitled", "none", "-"}
    clean = {k: v for k, v in meta.items()
             if v not in (None, "", []) and not (isinstance(v, str) and v.strip().lower() in junk)}
    if "title" in clean and not useful_title(clean["title"]):
        clean.pop("title")
    if isinstance(clean.get("keywords"), str):
        clean["keywords"] = [k.strip() for k in re.split(r"[;,]", clean["keywords"]) if k.strip()]
    return clean


_FILE_EXTS = (".indd", ".idml", ".qxp", ".qxd", ".doc", ".docx", ".odt", ".rtf", ".pdf", ".ppt", ".pptx",
              ".xls", ".xlsx", ".ai", ".psd", ".cdr", ".pub", ".tex", ".dvi", ".txt", ".htm", ".html", ".md",
              ".pages", ".key", ".numbers", ".wpd")
_BAD_TITLE_START = ("microsoft word", "microsoft powerpoint", "microsoft excel", "untitled", "sem título",
                    "sem titulo", "document", "documento1", "slide 1", "apresentação1", "pasta1")


def useful_title(title: Any) -> str:
    """Título dos metadados só se for um título de verdade — não um nome de arquivo do programa que
    gerou o PDF (“LGPD_revisado 1.indd”, “Microsoft Word - contrato.docx”, “C:\\pasta\\x.doc”)."""
    t = str(title or "").strip()
    low = t.lower()
    if len(t) <= 2 or low.startswith(_BAD_TITLE_START) or low.endswith(_FILE_EXTS) or "\\" in t or "/" in t:
        return ""
    return t


def frontmatter(meta: dict[str, Any], source: Path, converter: str, markdown: str,
                tags: list[str] | None = None, hide_source: bool = False) -> str:
    """`hide_source`: anonimização — não mostra o nome do arquivo de origem nem o usa como título."""
    title = meta.get("title") or _first_heading(markdown) or ("Documento" if hide_source else source.stem)
    data: dict[str, Any] = {"title": title}
    for k in ("author", "subject", "keywords", "created", "modified", "pages", "slides", "sheets"):
        if meta.get(k) not in (None, ""):
            data[k] = meta[k]
    data["source"] = ("documento" + source.suffix.lower()) if hide_source else source.name
    data["converter"] = f"Markinho ({converter})"
    data["converted"] = dt.datetime.now().replace(microsecond=0).isoformat()
    if tags:
        data["tags"] = tags
    lines = ["---"]
    for k, v in data.items():
        if isinstance(v, list):
            lines.append(f"{k}:")
            lines += [f"  - {json.dumps(str(i), ensure_ascii=False)}" for i in v]
        elif isinstance(v, (int, float)):
            lines.append(f"{k}: {v}")
        else:
            lines.append(f"{k}: {json.dumps(str(v), ensure_ascii=False)}")   # JSON é YAML válido
    lines.append("---")
    return "\n".join(lines) + "\n\n"


def _first_heading(md: str) -> str:
    for line in md.splitlines():
        if line.startswith("# "):
            return line[2:].strip()
    return ""


def strip_frontmatter(md: str) -> str:
    if md.startswith("---\n"):
        end = md.find("\n---", 4)
        if end != -1:
            return md[end + 4:].lstrip("\n")
    return md


# --------------------------------------------------------------------------- #
# Perfis
# --------------------------------------------------------------------------- #
def mdformat_text(md: str) -> str:
    try:
        import mdformat
    except ImportError:
        return md
    try:
        return mdformat.text(md, extensions={"gfm"}, options={"wrap": "keep", "number": False})
    except Exception:  # noqa: BLE001  - plugin gfm ausente ou erro de parse: tenta sem
        try:
            return mdformat.text(md, options={"wrap": "keep"})
        except Exception:  # noqa: BLE001
            return md


def strip_comments(md: str) -> str:
    """Remove <!-- … --> sem regex com retrocesso (com milhares de "<!--" abertos, o regex
    `<!--.*?-->` levava segundos ou minutos)."""
    out, pos = [], 0
    while True:
        start = md.find("<!--", pos)
        if start < 0:
            out.append(md[pos:])
            return "".join(out)
        out.append(md[pos:start])
        end = md.find("-->", start + 4)
        if end < 0:                       # comentário sem fim: o resto é comentário
            return "".join(out)
        pos = end + 3
        if md.startswith("\n", pos):
            pos += 1


_IMG_RE = re.compile(r"!\[([^\]]*)\]\(([^)\s]+)\)")


def apply_profile(md: str, profile: str) -> str:
    if profile == "mdformat":
        return mdformat_text(md)
    if profile == "obsidian":
        # imagens locais no formato de "embed" do Obsidian, que acha o arquivo em qualquer pasta do cofre
        return _IMG_RE.sub(lambda m: f"![[{Path(m.group(2)).name}]]" if not m.group(2).startswith(("http", "data:"))
                           else m.group(0), md)
    if profile == "llm":
        md = strip_comments(md)                                   # comentários (marcas de página etc.)
        md = re.sub(r"\n{3,}", "\n\n", md)
        return md
    return md


def finalize(raw: str, out: OutputOptions, files: dict[str, bytes], meta: dict[str, Any],
             source: Path, converter: str, hide_source: bool = False) -> str:
    """Texto final: imagens no modo escolhido, perfil e frontmatter."""
    mode = "none" if out.profile == "llm" else out.images
    md = render_images(raw, files, mode)
    md = apply_profile(md, out.profile)
    if out.frontmatter or out.profile == "obsidian":
        md = frontmatter(meta, source, converter, md, ["markinho"] if out.profile == "obsidian" else None,
                         hide_source) \
            + strip_frontmatter(md)
    md = re.sub(r"\n{3,}", "\n\n", md)
    return md.strip() + "\n"
