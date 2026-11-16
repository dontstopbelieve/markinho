# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 dontstopbelieve — Markinho
"""Servidor MCP local do Markinho.

Deixa assistentes de IA (Claude Desktop, Cursor, VS Code…) converterem documentos
usando o Markinho instalado — tudo no computador, nada vai para a internet.

    markinho --mcp            (no Windows instalado: markinho-cli.exe --mcp)

Segurança:
* o assistente só lê arquivos dentro das **pastas autorizadas** pelo usuário
  (janela “Assistentes de IA” do Markinho, ou a variável MARKINHO_MCP_FOLDERS);
* gravar arquivos (.md, DOCX, PDF…) só é possível se o usuário permitir, e também
  só dentro dessas pastas; arquivos existentes não são sobrescritos sem pedido;
* links simbólicos e caminhos com ".." são resolvidos antes da verificação.
"""
from __future__ import annotations

import contextlib
import json
import os
import sys
from pathlib import Path
from typing import Any

MAX_FILE_MB = 300


# --------------------------------------------------------------------------- #
# Configuração (pastas autorizadas)
# --------------------------------------------------------------------------- #
def config_path() -> Path:
    from .models import user_data_dir

    return user_data_dir() / "mcp.json"


def load_config() -> dict[str, Any]:
    cfg: dict[str, Any] = {"folders": [], "allow_write": False}
    try:
        cfg.update(json.loads(config_path().read_text(encoding="utf-8")))
    except (OSError, ValueError):
        pass
    env = os.environ.get("MARKINHO_MCP_FOLDERS")
    if env:
        cfg["folders"] = [p for p in env.split(os.pathsep) if p.strip()]
    if os.environ.get("MARKINHO_MCP_ALLOW_WRITE") in ("1", "true", "yes"):
        cfg["allow_write"] = True
    return cfg


def save_config(folders: list[str], allow_write: bool) -> Path:
    p = config_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps({"folders": folders, "allow_write": bool(allow_write)}, ensure_ascii=False, indent=2),
                 encoding="utf-8")
    return p


def allowed_folders() -> list[Path]:
    out = []
    for f in load_config()["folders"]:
        try:
            p = Path(f).expanduser().resolve()
        except OSError:
            continue
        if p.is_dir():
            out.append(p)
    return out


try:   # mensagens de ToolError chegam ao assistente; outras exceções viram um erro genérico
    from mcp.server.mcpserver.exceptions import ToolError as _ToolError
except ImportError:  # pragma: no cover - SDK do MCP não instalado (só a configuração é usada)
    _ToolError = Exception


class AccessDenied(_ToolError):
    pass


def _tool_errors(func):
    """Repassa ao assistente a explicação dos erros esperados (arquivo, conversão, permissão)."""
    import functools

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        from .core import ConversionError

        try:
            return func(*args, **kwargs)
        except _ToolError:
            raise
        except (ConversionError, ValueError, OSError, RuntimeError) as exc:
            raise _ToolError(str(exc)) from exc
    return wrapper


def check_path(path: str, write: bool = False, must_exist: bool = True) -> Path:
    """Resolve o caminho e confere se está dentro de uma pasta autorizada."""
    folders = allowed_folders()
    if not folders:
        raise AccessDenied("Nenhuma pasta autorizada. Abra o Markinho > Assistentes de IA e adicione as pastas "
                           "que o assistente pode usar.")
    if "\x00" in path:
        raise AccessDenied("Caminho inválido.")
    p = Path(path).expanduser()
    if not p.is_absolute():
        p = folders[0] / p          # relativo: dentro da primeira pasta autorizada
    p = p.resolve()                 # resolve ".." e links simbólicos ANTES de verificar
    if not any(p == f or p.is_relative_to(f) for f in folders):
        raise AccessDenied(f"Acesso negado: {p} está fora das pastas autorizadas ({', '.join(map(str, folders))}).")
    if write and not load_config().get("allow_write"):
        raise AccessDenied("Gravar arquivos não está permitido. Ative “Permitir salvar arquivos” em "
                           "Markinho > Assistentes de IA.")
    if must_exist and not p.is_file():
        raise AccessDenied(f"Arquivo não encontrado: {p}")
    if must_exist and p.stat().st_size > MAX_FILE_MB * 1024 * 1024:
        raise AccessDenied(f"Arquivo maior que {MAX_FILE_MB} MB.")
    return p


@contextlib.contextmanager
def _quiet():
    """No modo stdio, a saída padrão é o canal do protocolo: nada pode ser impresso nela."""
    with contextlib.redirect_stdout(sys.stderr):
        yield


# --------------------------------------------------------------------------- #
# Servidor
# --------------------------------------------------------------------------- #
INSTRUCTIONS = (
    "Markinho converts local documents (PDF, Word, Excel, PowerPoint, OpenDocument, RTF, HTML, EPUB, images "
    "with OCR, legacy .doc/.xls/.ppt) to clean Markdown, entirely on this computer. Only files inside the "
    "folders the user authorized can be read. Use list_documents to discover files, convert_document to read "
    "one as Markdown, convert_to_chunks for RAG-ready chunks, and export_markdown to write Markdown to DOCX/PDF/"
    "HTML/etc. (only if the user allowed writing)."
)


def build_server():
    from mcp.server import MCPServer
    from mcp.types import ToolAnnotations

    from . import __version__

    server = MCPServer("Markinho", title="Markinho — Conversor Markdown (local)", instructions=INSTRUCTIONS,
                       version=__version__, website_url="https://github.com/dontstopbelieve/markinho",
                       log_level="WARNING")
    read_only = ToolAnnotations(read_only_hint=True, destructive_hint=False, idempotent_hint=True,
                                open_world_hint=False)

    @server.tool(annotations=read_only)
    @_tool_errors
    def markinho_info() -> dict[str, Any]:
        """Show Markinho's edition, available conversion engines, OCR, export formats and the folders the
        assistant is allowed to access."""
        from . import ocr
        from .edition import label
        from .engines import ENGINES
        from .exporter import available_formats

        engines = {e.id: {"available": e.available()[0], "status": e.available()[1],
                          "extensions": sorted(e.extensions()) if e.available()[0] else []}
                   for e in ENGINES.values()}
        cfg = load_config()
        return {"version": __version__, "edition": label(), "engines": engines, "ocr": ocr.describe_status(),
                "export_formats": [f.id for f in available_formats()],
                "allowed_folders": [str(f) for f in allowed_folders()], "write_allowed": bool(cfg["allow_write"])}

    @server.tool(annotations=read_only)
    @_tool_errors
    def list_documents(folder: str = "", pattern: str = "*", recursive: bool = True, limit: int = 200) -> dict[str, Any]:
        """List convertible documents inside the authorized folders.

        folder: a folder inside an authorized folder (empty = all authorized folders).
        pattern: glob filter on the file name, e.g. "*.pdf" or "relatorio*".
        """
        from .engines import all_input_extensions

        exts = set(all_input_extensions())
        if any(c in pattern for c in "/\\") or ".." in pattern:
            raise AccessDenied("O filtro deve ser só um nome de arquivo (ex.: *.pdf), sem pastas ou “..”.")
        roots = [check_path(folder, must_exist=False)] if folder else allowed_folders()
        allowed = allowed_folders()
        if not roots:
            raise AccessDenied("Nenhuma pasta autorizada.")
        files = []
        for root in roots:
            it = root.rglob(pattern) if recursive else root.glob(pattern)
            for f in it:
                if len(files) >= max(1, min(limit, 2000)):
                    break
                if not (f.is_file() and f.suffix.lower() in exts) or any(part.startswith(".") for part in f.parts):
                    continue
                real = f.resolve()             # link simbólico apontando para fora: não aparece
                if any(real == a or real.is_relative_to(a) for a in allowed):
                    st = f.stat()
                    files.append({"path": str(f), "size_kb": round(st.st_size / 1024, 1),
                                  "modified": int(st.st_mtime)})
        return {"count": len(files), "files": files, "truncated": len(files) >= limit}

    @server.tool(annotations=read_only)
    @_tool_errors
    def convert_document(path: str, engine: str = "auto", profile: str = "gfm", frontmatter: bool = False,
                         pages: str = "", max_chars: int = 200_000) -> str:
        """Convert a local document to Markdown and return the text.

        path: absolute path, or relative to the first authorized folder.
        engine: "auto" (recommended), "native", "anydoc", "pandoc", "docling", "markitdown"…
        profile: "gfm" (default), "llm" (no images/comments, fewer tokens), "mdformat" or "obsidian".
        frontmatter: add YAML metadata (title, author, dates, pages) at the top.
        pages: PDF page range for the native engine, e.g. "1-3,5" (empty = all).
        max_chars: truncate very long results (the response says so).
        """
        from .core import convert
        from .postprocess import OutputOptions
        from .textfix import FixOptions

        p = check_path(path)
        opts = {"pages": pages} if pages else {}
        with _quiet():
            r = convert(p, engine, opts, FixOptions(), OutputOptions(images="none", profile=profile,
                                                                      frontmatter=frontmatter))
        md = r.markdown
        if len(md) > max_chars:
            md = md[:max_chars] + f"\n\n[… truncado: {len(r.markdown):,} caracteres no total; use max_chars maior ou pages]"
        return md

    @server.tool(annotations=read_only)
    @_tool_errors
    def convert_to_chunks(path: str, chunk_size: int = 1500, overlap: int = 150, strategy: str = "title",
                          engine: str = "auto", max_chunks: int = 500) -> dict[str, Any]:
        """Convert a local document and split it into RAG-ready chunks (with heading path, page and source).

        strategy: "title" (sections, default), "page" or "basic" (size only).
        """
        from .chunker import chunk_markdown
        from .core import convert
        from .postprocess import OutputOptions
        from .textfix import FixOptions

        p = check_path(path)
        with _quiet():
            r = convert(p, engine, {"pdf_page_markers": strategy == "page"} if engine in ("auto", "native") else {},
                        FixOptions(), OutputOptions(images="none"))
        chunks = chunk_markdown(r.markdown, chunk_size, overlap, strategy, source=p.name)
        return {"document": {**r.metadata, "source": p.name, "converter": r.converter},
                "total": len(chunks), "chunks": [c.to_dict() for c in chunks[:max(1, max_chunks)]]}

    @server.tool(annotations=ToolAnnotations(read_only_hint=False, destructive_hint=False, idempotent_hint=False,
                                             open_world_hint=False))
    @_tool_errors
    def export_markdown(markdown: str, output_path: str, format: str = "docx", title: str = "",
                        overwrite: bool = False) -> str:
        """Write Markdown to a file in another format (docx, pdf, html, odt, epub, pptx, latex, rst, plain,
        chunks_jsonl…). Only allowed if the user enabled writing, and only inside the authorized folders.
        Existing files are not replaced unless overwrite=true."""
        from .exporter import FORMATS_BY_ID, export

        if format not in FORMATS_BY_ID:
            raise ValueError(f"Formato desconhecido: {format}. Opções: {', '.join(FORMATS_BY_ID)}")
        target = check_path(output_path, write=True, must_exist=False)
        if target.suffix.lower() != FORMATS_BY_ID[format].ext:
            target = target.with_suffix(FORMATS_BY_ID[format].ext)
            target = check_path(str(target), write=True, must_exist=False)
        if target.exists() and not overwrite:
            raise AccessDenied(f"{target} já existe (use overwrite=true para substituir).")
        target.parent.mkdir(parents=True, exist_ok=True)
        with _quiet():
            # imagens só das pastas autorizadas: o Markdown pode ter vindo de um documento malicioso
            via = export(markdown, target, format, {"title": title} if title else {},
                         base_dir=target.parent, allowed_dirs=allowed_folders())
        return f"Arquivo gravado: {target} (via {'Pandoc' if via == 'pandoc' else 'exportador nativo'})"

    @server.tool(annotations=ToolAnnotations(read_only_hint=False, destructive_hint=False, idempotent_hint=True,
                                             open_world_hint=False))
    @_tool_errors
    def save_markdown(path: str, output_folder: str = "", engine: str = "auto", frontmatter: bool = True,
                      overwrite: bool = False, name_template: str = "{nome}", safe_names: bool = False) -> str:
        """Convert a document and save the .md file (with an <name>_assets folder for its images) next to it,
        or in output_folder. Requires write permission.

        name_template: output name pattern, e.g. "{nome}" (original name), "{data}_{nome}", "{titulo}".
          Tokens: {nome} {original} {titulo} {data} {pasta} {motor} {n}.
        safe_names: no accents/spaces, lowercase."""
        from .naming import NameContext, NamingOptions, rename_assets, render, validate

        if err := validate(name_template):
            raise ValueError(err)
        from .assets import write_assets
        from .core import convert
        from .postprocess import OutputOptions
        from .textfix import FixOptions

        src = check_path(path)
        folder = check_path(output_folder, write=True, must_exist=False) if output_folder else \
            check_path(str(src.parent), write=True, must_exist=False)
        with _quiet():
            r = convert(src, engine, None, FixOptions(), OutputOptions(images="folder", frontmatter=frontmatter))
        ctx = NameContext.from_result(src, title=r.metadata.get("title") or r.title, engine=r.engine)
        target = check_path(str(folder / (render(ctx, 0, NamingOptions(name_template, safe=safe_names)) + ".md")),
                            write=True, must_exist=False)
        if target.exists() and not overwrite:
            raise AccessDenied(f"{target} já existe (use overwrite=true para substituir).")
        folder.mkdir(parents=True, exist_ok=True)
        md, files = rename_assets(r.markdown, r.assets, target.stem)
        target.write_text(md, encoding="utf-8")
        n = write_assets(md, files, folder)
        return f"Salvo: {target}" + (f" e {n} imagem(ns) na pasta {target.stem}_assets" if n else "")

    return server


def run() -> int:
    from .models import setup_environment

    setup_environment()
    import logging

    logging.basicConfig(stream=sys.stderr, level=logging.WARNING)
    if not allowed_folders():
        print("Markinho MCP: nenhuma pasta autorizada ainda — o assistente não conseguirá ler arquivos até "
              "você autorizar pastas em Markinho > Assistentes de IA.", file=sys.stderr)
    build_server().run("stdio")
    return 0


# --------------------------------------------------------------------------- #
# Configuração dos assistentes (Claude Desktop, Cursor, VS Code)
# --------------------------------------------------------------------------- #
def server_command() -> tuple[str, list[str]]:
    """Comando que o assistente deve executar para iniciar o servidor."""
    if getattr(sys, "frozen", False):
        exe = Path(sys.executable).parent / ("markinho-cli.exe" if os.name == "nt" else "markinho-cli")
        return str(exe), ["--mcp"]
    return sys.executable, ["-m", "markinho", "--mcp"]


def client_config(kind: str = "claude") -> dict[str, Any]:
    cmd, args = server_command()
    entry: dict[str, Any] = {"command": cmd, "args": args}
    if not getattr(sys, "frozen", False):
        # rodando pelo código-fonte: o assistente precisa achar o pacote markinho
        entry["env"] = {"PYTHONPATH": str(Path(__file__).resolve().parent.parent)}
    if kind == "vscode":
        return {"servers": {"markinho": {"type": "stdio", **entry}}}
    return {"mcpServers": {"markinho": entry}}


def claude_desktop_config_path() -> Path:
    if sys.platform == "win32":
        return Path(os.environ.get("APPDATA") or Path.home() / "AppData" / "Roaming") / "Claude" / \
            "claude_desktop_config.json"
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / "Claude" / "claude_desktop_config.json"
    return Path(os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config") / "Claude" / "claude_desktop_config.json"


def install_claude_desktop(path: Path | None = None) -> Path:
    """Acrescenta o Markinho à configuração do Claude Desktop (mantém os outros servidores e faz backup)."""
    path = path or claude_desktop_config_path()
    data: dict[str, Any] = {}
    if path.exists():
        raw = path.read_text(encoding="utf-8")
        try:
            data = json.loads(raw) if raw.strip() else {}
        except ValueError as exc:
            raise RuntimeError(f"O arquivo {path} não é um JSON válido; corrija-o antes.") from exc
        path.with_suffix(".json.bak").write_text(raw, encoding="utf-8")
    data.setdefault("mcpServers", {})["markinho"] = client_config("claude")["mcpServers"]["markinho"]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return path
