# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 dontstopbelieve — Markinho
"""Núcleo do Markinho: registro dos conversores nativos e a função `convert`.

Fluxo de uma conversão:

    motor (Nativo/Pandoc/Docling/Marker/MarkItDown/PyMuPDF4LLM)
      → imagens viram ativos (pasta, base64 ou nenhuma)
      → descrição das imagens por IA local (opcional, Ollama)
      → texto bruto (`raw_markdown`)
      → correção de caracteres (opcional)
      → perfil de saída + frontmatter YAML  → `markdown`
"""
from __future__ import annotations

from .i18n import tr

import contextvars
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

ConverterFunc = Callable[[Path], str]

# opções do motor nativo e destino das imagens durante uma conversão
_OPTIONS: contextvars.ContextVar[dict[str, Any]] = contextvars.ContextVar("markinho_options", default={})
_SINK: contextvars.ContextVar[Any] = contextvars.ContextVar("markinho_sink", default=None)
# avisos com página (para “revise aqui”), progresso por página e pedido de parada
_NOTES: contextvars.ContextVar[Any] = contextvars.ContextVar("markinho_notes", default=None)
_PROGRESS: contextvars.ContextVar[Any] = contextvars.ContextVar("markinho_progress", default=None)
_PARTIAL: contextvars.ContextVar[Any] = contextvars.ContextVar("markinho_partial", default=None)
_CANCEL: contextvars.ContextVar[Any] = contextvars.ContextVar("markinho_cancel", default=None)
_PAGES: contextvars.ContextVar[Any] = contextvars.ContextVar("markinho_pages", default=None)

CANCELLED = tr("Conversão interrompida pelo usuário.")
# erros em que outro motor não ajudaria (senha, arquivo ausente, formato recusado, segurança);
# português e inglês, porque a mensagem vem traduzida
_NO_RETRY = ("senha", "não encontrado", "não aceita", "segurança",
             "password", "not found", "does not accept", "security")


INFO = "ℹ "        # avisos só informativos começam com este sinal (não mostram ⚠)


def warn(message: str, pages: list[int] | None = None, info: bool = False) -> None:
    """Registra um aviso da conversão atual; `pages` (1, 2…) são as páginas a revisar.
    `info=True`: só informação (ex.: “carimbos removidos”), sem o ícone de alerta."""
    notes = _NOTES.get()
    if notes is not None:
        notes.append(((INFO if info else "") + message, sorted(set(pages or []))))


def is_alert(message: str) -> bool:
    return not message.startswith(INFO)


def record_page_starts(starts: list[tuple[int, str]]) -> None:
    """Onde cada página começa no texto (página, trecho inicial) — para o original acompanhar a leitura."""
    box = _PAGES.get()
    if box is not None:
        box[:] = starts


def report_partial(page: int, text: str) -> None:
    """Texto provisório de uma página já lida (prévia enquanto o resto converte)."""
    cb = _PARTIAL.get()
    if cb is not None:
        try:
            cb(page, text)
        except Exception:  # noqa: BLE001
            pass


def report_progress(done: int, total: int) -> None:
    """Progresso dentro de um arquivo (ex.: página 12 de 80)."""
    cb = _PROGRESS.get()
    if cb is not None:
        try:
            cb(done, total)
        except Exception:  # noqa: BLE001
            pass


def check_cancel() -> None:
    """Interrompe a conversão se o usuário pediu para parar."""
    ev = _CANCEL.get()
    if ev is not None and ev.is_set():
        raise ConversionError(CANCELLED)


class ConversionError(Exception):
    """Erro ao converter um arquivo."""


@dataclass
class ConversionResult:
    source: Path
    markdown: str                 # texto final (correções, perfil, frontmatter, imagens)
    converter: str                # ex.: "Nativo › PDF", "Pandoc", "Docling"
    seconds: float = 0.0
    raw_markdown: str = ""        # texto como saiu do motor (já com imagens como ativos)
    fix_report: Any = None        # textfix.FixReport ou None
    anon_report: Any = None       # anonymize.AnonReport ou None (anonimização desligada)
    engine: str = "native"
    assets: dict[str, bytes] = field(default_factory=dict)   # "nome_assets/imagem_001.png" -> bytes
    metadata: dict[str, Any] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    review_pages: list[int] = field(default_factory=list)    # páginas a revisar (OCR fraco, sem texto…)
    page_starts: list[tuple[int, str]] = field(default_factory=list)   # (página, trecho) para rolar junto
    fix: Any = None               # FixOptions usadas
    output: Any = None            # OutputOptions usadas

    @property
    def title(self) -> str:
        for line in self.markdown.splitlines():
            if line.startswith("#"):
                return line.lstrip("#").strip()
        return self.source.stem


@dataclass
class _Converter:
    name: str
    extensions: tuple[str, ...]
    func: ConverterFunc


_REGISTRY: dict[str, _Converter] = {}


def register(name: str, *extensions: str):
    """Decorador para registrar um conversor nativo para uma ou mais extensões."""

    def deco(func: ConverterFunc) -> ConverterFunc:
        conv = _Converter(name, tuple(e.lower() for e in extensions), func)
        for ext in conv.extensions:
            _REGISTRY[ext] = conv
        return func

    return deco


def option(key: str, default: Any = None) -> Any:
    """Lê uma opção do motor nativo dentro de um conversor."""
    return _OPTIONS.get().get(key, default)


def current_sink():
    """Destino das imagens da conversão atual (`assets.AssetSink`) ou None."""
    return _SINK.get()


def supported_extensions() -> list[str]:
    """Extensões aceitas pelo motor nativo."""
    _ensure_loaded()
    return sorted(_REGISTRY)


def _ensure_loaded() -> None:
    if not _REGISTRY:
        from . import converters  # noqa: F401  (registra os conversores)


def native_name(ext: str) -> str:
    _ensure_loaded()
    conv = _REGISTRY.get(ext.lower())
    return conv.name if conv else ext


def convert_native(path: Path, opts: dict[str, Any] | None = None) -> str:
    _ensure_loaded()
    conv = _REGISTRY.get(path.suffix.lower())
    if conv is None:
        raise ConversionError(tr("Formato não suportado pelo motor nativo: '{0}'").format(path.suffix or path.name))
    token = _OPTIONS.set(dict(opts or {}))
    try:
        return conv.func(path)
    finally:
        _OPTIONS.reset(token)


def convert(path: str | Path, engine: str = "auto", engine_options: dict[str, Any] | None = None,
            fix: Any = None, output: Any = None, fallback: bool | None = None,
            progress: Callable[[int, int], None] | None = None, cancel: Any = None,
            partial: Callable[[int, str], None] | None = None) -> ConversionResult:
    """Converte `path` para Markdown.

    engine:          "auto" ou o id de um motor (veja `engines.ENGINES`).
    engine_options:  opções do motor (veja `engines.ENGINES[id].options`).
    fix:             `textfix.FixOptions` para corrigir caracteres, ou None.
    output:          `postprocess.OutputOptions` (imagens, frontmatter, perfil, descrição).
    fallback:        se o motor falhar, tenta os outros motores leves que leem o formato
                     (padrão: sim no modo automático).
    progress:        função (feitas, total) chamada a cada página (motor nativo).
    cancel:          `threading.Event`; quando ligado, a conversão para na próxima página.
    partial:         função (página, texto provisório) chamada a cada página lida (PDF nativo).
    """
    from .engines import ENGINES, pick_engine

    if fallback is None:
        fallback = engine == "auto"
    t_prog, t_cancel, t_part = _PROGRESS.set(progress), _CANCEL.set(cancel), _PARTIAL.set(partial)
    try:
        return _convert_with_fallback(path, engine, engine_options, fix, output, fallback)
    finally:
        _PROGRESS.reset(t_prog)
        _CANCEL.reset(t_cancel)
        _PARTIAL.reset(t_part)


def _convert_with_fallback(path, engine, engine_options, fix, output, fallback) -> ConversionResult:
    from .engines import ENGINES, pick_engine

    try:
        return _convert_once(path, engine, engine_options, fix, output)
    except ConversionError as exc:
        msg = str(exc).lower()
        if not fallback or any(k in msg for k in _NO_RETRY) or str(exc) == CANCELLED:
            raise
        first = engine if engine != "auto" else None
        try:
            first = first or pick_engine(Path(path)).id
        except RuntimeError:
            raise exc from None
        for alt in ENGINES.values():
            if alt.id == first or alt.heavy or not alt.available()[0] or not alt.supports(Path(path)):
                continue
            try:
                r = _convert_once(path, alt.id, None, fix, output)
            except ConversionError:
                continue
            r.warnings.insert(0, tr('{0} não conseguiu ler o arquivo ({1}); convertido com {2}.').format(ENGINES[first].name, exc, alt.name))
            return r
        raise


def _convert_once(path: str | Path, engine: str = "auto", engine_options: dict[str, Any] | None = None,
                  fix: Any = None, output: Any = None) -> ConversionResult:
    from .assets import AssetSink, absorb_images, set_alt_texts
    from .engines import pick_engine
    from .postprocess import OutputOptions, extract_metadata

    path = Path(path)
    out = output or OutputOptions()
    if not path.is_file():
        raise ConversionError(tr('Arquivo não encontrado: {0}').format(path))
    from .safety import UnsafeFileError, check_zip

    try:
        check_zip(path)
    except UnsafeFileError as exc:
        raise ConversionError(tr('Arquivo recusado por segurança: {0}. Ele não foi aberto.').format(exc)) from None
    try:
        eng = pick_engine(path, engine)
    except RuntimeError as exc:
        raise ConversionError(str(exc)) from exc
    opts = eng.defaults()
    opts.update(engine_options or {})
    sink = AssetSink(path.stem, enabled=out.images != "none")
    start = time.perf_counter()
    warnings: list[str] = []
    with tempfile.TemporaryDirectory(prefix="markinho_") as tmp:
        opts["_extract_images"] = sink.enabled
        opts["_tmpdir"] = tmp
        notes: list[tuple[str, list[int]]] = []
        pages: list[tuple[int, str]] = []
        token = _SINK.set(sink)
        t_notes = _NOTES.set(notes)
        t_pages = _PAGES.set(pages)
        try:
            raw = eng.convert(path, opts)
        except ImportError as exc:
            raise ConversionError(tr("Dependência ausente para o motor {0}: {1}. Instale com: {2}").format(
                eng.name, exc.name, eng.install_hint or "pip install -r requirements.txt")) from exc
        except ConversionError:
            raise
        except Exception as exc:  # noqa: BLE001
            msg = tr('{0} falhou ao converter {1}: {2}').format(eng.name, path.name, exc)
            if eng.heavy and any(k in f"{type(exc).__name__} {exc}" for k in
                                 ("403", "Proxy", "Connect", "Timeout", "resolve", "HfHub", "LocalEntryNotFound")):
                msg += (tr(' — Não foi possível baixar os modelos de IA. Na primeira execução o {0} precisa de internet para baixá-los (ou use “Baixar modelos” em Motores, num computador com internet, e copie a pasta de modelos).').format(eng.name))
            raise ConversionError(msg) from exc
        finally:
            _SINK.reset(token)
            _NOTES.reset(t_notes)
            _PAGES.reset(t_pages)
        if sink.enabled:
            raw = absorb_images(raw, sink, [path.parent, Path(tmp)])
    raw = normalize(raw)

    if out.describe_images and sink.files:
        from .describe import describe_all

        model = out.ollama_model
        if not model:
            from .describe import vision_models

            models = vision_models(out.ollama_url)
            model = models[0] if models else ""
        if model:
            alts, errs = describe_all(sink.files, model, out.ollama_url)
            raw = set_alt_texts(raw, alts)
            warnings += [tr('Descrição de imagens: {0}').format(e) for e in errs]
        else:
            warnings.append(tr("Descrição de imagens: Ollama não encontrado ou sem modelo de visão "
                            "(ex.: ollama pull qwen2.5vl:3b)."))

    label = eng.name
    if eng.id == "native":
        label = tr("Nativo") + f" › {native_name(path.suffix)}"
    review = sorted({p for _, pages in notes for p in pages})
    warnings = [m for m, _ in notes] + warnings
    result = ConversionResult(path, raw, label, 0.0, raw_markdown=raw, engine=eng.id, assets=dict(sink.files),
                              metadata=extract_metadata(path), warnings=warnings, review_pages=review,
                              page_starts=list(pages))
    finalize_result(result, fix, out)
    result.seconds = time.perf_counter() - start
    return result


def finalize_result(result: ConversionResult, fix: Any = None, output: Any = None) -> ConversionResult:
    """(Re)gera o texto final a partir do bruto — rápido, sem reconverter o arquivo."""
    from .postprocess import OutputOptions, finalize
    from .textfix import fix_text

    result.fix = fix
    result.output = output or result.output or OutputOptions()
    text = result.raw_markdown
    if fix is None:
        result.fix_report = None
    else:
        text, result.fix_report = fix_text(text, fix)
    out, meta, hide = result.output, result.metadata, False
    result.anon_report = None
    anon = getattr(out, "anon", None)
    if anon is not None:
        import dataclasses

        from .anonymize import anonymize, clean_metadata, strip_image_metadata

        text, result.anon_report = anonymize(text, anon)
        if anon.image_metadata:
            result.assets = {k: strip_image_metadata(v) for k, v in result.assets.items()}
        if anon.remove_images:
            out = dataclasses.replace(out, images="none")
        if anon.metadata:
            meta, hide = clean_metadata(meta), True
    result.markdown = finalize(normalize(text), out, result.assets, meta,
                               result.source, result.converter, hide_source=hide)
    return result


def apply_fix(result: ConversionResult, fix: Any) -> ConversionResult:
    """Compatibilidade: reaplica só a correção de caracteres."""
    return finalize_result(result, fix, result.output)


def normalize(md: str) -> str:
    """Remove espaços no fim das linhas, excesso de linhas em branco e garante
    linha em branco antes de tabelas."""
    lines = [ln.rstrip() for ln in md.replace("\r\n", "\n").replace("\r", "\n").split("\n")]
    out: list[str] = []
    blank = 0
    in_code = False
    for ln in lines:
        if ln.lstrip().startswith(("```", "~~~")):
            in_code = not in_code
        if not in_code and ln.startswith("|") and out and out[-1] and not out[-1].startswith("|"):
            out.append("")
            blank = 1
        blank = blank + 1 if not ln else 0
        if blank <= 1 or in_code:
            out.append(ln)
    return "\n".join(out).strip() + "\n"
