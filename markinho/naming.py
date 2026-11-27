# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 dontstopbelieve — Markinho
"""Nomes dos arquivos de saída.

Um *padrão* define o nome de cada arquivo gerado, com marcadores entre chaves:

    {nome}      nome do arquivo original, sem extensão (ou o nome dado ao renomear na lista)
    {original}  nome original completo, com extensão (ex.: contrato.pdf)
    {n}         número na ordem da lista, com zeros à esquerda (001, 002…); {n:02} escolhe os dígitos
    {titulo}    título do documento (metadados ou primeiro título do texto)
    {data}      data de hoje (AAAA-MM-DD)
    {pasta}     nome da pasta do arquivo original
    {motor}     motor usado na conversão (nativo, anydoc, pandoc…)

Exemplos: "{nome}" → contrato.md · "{n}_{nome}" → 001_contrato.md ·
"Cliente-{data}-{nome}" → Cliente-2026-11-13-contrato.md
"""
from __future__ import annotations

from .i18n import tr

import datetime as dt
import re
import string
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path

TOKENS = ["nome", "original", "n", "titulo", "data", "pasta", "motor"]
EXTENSIONS = [".md", ".markdown", ".txt"]
CONFLICTS = [("suffix", tr("Acrescentar _2, _3…")), ("overwrite", tr("Substituir")), ("skip", tr("Pular"))]
PRESETS = [("{nome}", tr("Manter o nome")), ("{n}_{nome}", tr("Número + nome")), ("{n} - {titulo}", tr("Número + título")),
           ("{data}_{nome}", "Data + nome"), ("{nome}_{data}", "Nome + data")]

_INVALID = re.compile(r'[<>:"/\\|?*\x00-\x1f]+')
_RESERVED = {"con", "prn", "aux", "nul", *(f"com{i}" for i in range(1, 10)), *(f"lpt{i}" for i in range(1, 10))}


@dataclass
class NamingOptions:
    template: str = "{nome}"
    ext: str = ".md"
    start: int = 1
    digits: int = 3
    safe: bool = False          # sem acentos/espaços, minúsculas (bom para indexação e servidores)
    conflict: str = "suffix"    # suffix | overwrite | skip


@dataclass
class NameContext:
    stem: str                   # nome original sem extensão
    original: str = ""          # nome original com extensão
    title: str = ""
    folder: str = ""
    engine: str = ""
    custom: str = ""            # nome dado pelo usuário ao renomear o item
    date: dt.date = field(default_factory=dt.date.today)

    @classmethod
    def from_result(cls, source: Path, title: str = "", engine: str = "", custom: str = "") -> "NameContext":
        source = Path(source)
        return cls(source.stem, source.name, title, source.parent.name, engine, custom)


class _Number(int):
    """{n} usa os dígitos configurados; {n:02} escolhe outro formato."""
    digits = 3

    def __format__(self, spec: str) -> str:
        if not spec:
            return f"{int(self):0{self.digits}d}"
        return format(int(self), spec)


def validate(template: str) -> str | None:
    """Mensagem de erro se o padrão for inválido, senão None."""
    if not template.strip():
        return tr("O padrão não pode ficar vazio.")
    try:
        parsed = list(string.Formatter().parse(template))
        fields = [f for _, f, _, _ in parsed if f is not None]
        if any("{" in (spec or "") for _, _, spec, _ in parsed):
            return tr("Padrão inválido: não use marcadores dentro de outro marcador.")
    except ValueError as exc:
        return tr('Padrão inválido: {0}').format(exc)
    unknown = [f for f in fields if f.split("!")[0] not in TOKENS]
    if unknown:
        return f"Marcador desconhecido: {{{unknown[0]}}}. Use: " + ", ".join("{" + t + "}" for t in TOKENS)
    return None


def slugify(text: str) -> str:
    text = unicodedata.normalize("NFKD", text)
    text = "".join(c for c in text if not unicodedata.combining(c))
    text = re.sub(r"[^\w.-]+", "-", text.lower(), flags=re.ASCII)
    text = re.sub(r"-{2,}", "-", text)
    text = re.sub(r"-*\.-*", ".", text)          # "v2-.pdf" -> "v2.pdf"
    return text.strip("-._")


def clean(name: str) -> str:
    name = _INVALID.sub("_", name)
    name = re.sub(r"\s+", " ", name).strip(" ._")
    if name.lower() in _RESERVED:                 # nomes proibidos no Windows
        name = f"_{name}"
    return name[:150].rstrip(" ._")


def render(ctx: NameContext, index: int, opts: NamingOptions) -> str:
    """Nome (sem extensão) para o item na posição `index` (0 = primeiro da lista)."""
    num = _Number(opts.start + index)
    num.digits = max(1, min(int(opts.digits), 9))
    base = ctx.custom or ctx.stem
    values = {"nome": base, "original": ctx.original or base, "n": num, "titulo": ctx.title or base,
              "data": ctx.date.isoformat(), "pasta": ctx.folder, "motor": ctx.engine}
    if validate(opts.template):
        name = base
    else:
        try:
            name = opts.template.format_map(values)
        except (ValueError, KeyError, IndexError):
            name = base
    name = slugify(name) if opts.safe else clean(name)
    return name or "documento"


@dataclass
class Planned:
    name: str          # nome final com extensão
    path: Path | None  # caminho completo (se houver pasta de destino)
    action: str        # "write" | "overwrite" | "skip"


def plan(contexts: list[NameContext], opts: NamingOptions, target_dir: Path | None = None,
         ext: str | None = None) -> list[Planned]:
    """Calcula os nomes de todos os itens, resolvendo repetições e arquivos já existentes."""
    ext = ext if ext is not None else opts.ext
    used: set[str] = set()
    out: list[Planned] = []
    for i, ctx in enumerate(contexts):
        stem = render(ctx, i, opts)
        name, k = stem + ext, 2
        while name.lower() in used:                    # dois itens com o mesmo nome no lote
            name, k = f"{stem}_{k}{ext}", k + 1
        action = "write"
        if target_dir is not None and (Path(target_dir) / name).exists():
            if opts.conflict == "overwrite":
                action = "overwrite"
            elif opts.conflict == "skip":
                action = "skip"
            else:
                while name.lower() in used or (Path(target_dir) / name).exists():
                    name, k = f"{stem}_{k}{ext}", k + 1
        used.add(name.lower())
        out.append(Planned(name, Path(target_dir) / name if target_dir is not None else None, action))
    return out


def rename_assets(md: str, files: dict[str, bytes], new_stem: str) -> tuple[str, dict[str, bytes]]:
    """Renomeia a pasta de imagens (<nome>_assets/) para acompanhar o novo nome do arquivo e
    corrige os links dentro do Markdown."""
    if not files:
        return md, files
    from .assets import safe_stem

    old_folders = {k.split("/", 1)[0] for k in files if "/" in k}
    new_folder = f"{safe_stem(new_stem)}_assets"     # sem espaços: links Markdown não aceitam espaço
    new_files: dict[str, bytes] = {}
    for k, v in files.items():
        folder, _, rest = k.partition("/")
        new_files[f"{new_folder}/{rest}" if rest and folder in old_folders else k] = v
    for old in old_folders:
        if old != new_folder:
            md = md.replace(f"]({old}/", f"]({new_folder}/").replace(f"](<{old}/", f"](<{new_folder}/")
    return md, new_files
