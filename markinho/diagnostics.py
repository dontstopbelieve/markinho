# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 dontstopbelieve — Markinho
"""“Gerar relatório de erro”: um texto para o usuário enviar ao suporte, se quiser.

Contém versão, edição, sistema, motores disponíveis, configurações (sem pastas) e os últimos
erros e registros — **sem o conteúdo dos documentos**. Caminhos de arquivos aparecem só pelo nome,
e a pasta do usuário vira “~”. O usuário vê o texto inteiro antes de salvar; nada é enviado.
"""
from __future__ import annotations

import collections
import datetime as dt
import logging
import os
import platform
import sys
import traceback
from pathlib import Path

_LOG: collections.deque[str] = collections.deque(maxlen=400)
_ERRORS: collections.deque[str] = collections.deque(maxlen=50)
_installed = False


class _Ring(logging.Handler):
    def emit(self, record: logging.LogRecord) -> None:
        try:
            _LOG.append(self.format(record))
        except Exception:  # noqa: BLE001
            pass


def install() -> None:
    """Começa a guardar (só na memória) os registros recentes do Markinho e erros inesperados."""
    global _installed
    if _installed:
        return
    _installed = True
    h = _Ring(level=logging.INFO)
    h.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s", "%H:%M:%S"))
    for name in ("markinho", "docling", "pypandoc", "pdfminer", "PIL"):
        lg = logging.getLogger(name)
        lg.addHandler(h)
        if lg.level == logging.NOTSET or lg.level > logging.INFO:
            lg.setLevel(logging.INFO if name == "markinho" else logging.WARNING)
    old = sys.excepthook

    def hook(etype, value, tb):
        record_error("(programa)", f"{etype.__name__}: {value}", "".join(traceback.format_tb(tb)))
        old(etype, value, tb)

    sys.excepthook = hook


import re

# pasta do usuário em qualquer formato: C:\Users\Nome, C:\\Users\\Nome (texto escapado), C:/Users/Nome,
# /home/nome, /Users/nome (macOS)
_USER_DIR = re.compile(r"(?i)([a-z]:(?:\\{1,2}|/)(?:users|documents and settings)(?:\\{1,2}|/))[^\\/\"'\n]+"
                       r"|(/(?:home|Users)/)[^/\"'\s]+")


def _redact(text: str) -> str:
    """Tira o nome do usuário dos caminhos (privacidade)."""
    home = str(Path.home())
    if home and len(home) > 3:
        for variant in {home, home.replace("\\", "\\\\"), home.replace("\\", "/")}:
            text = text.replace(variant, "~")
    return _USER_DIR.sub(lambda m: (m.group(1) or m.group(2)) + "<usuário>", text)


def record_error(source: str, message: str, tb: str = "", context: dict | None = None) -> None:
    """Guarda um erro de conversão: nome, tipo e tamanho do arquivo, mensagem, detalhes técnicos e a
    configuração usada naquela conversão (motor, opções, saída). Nunca o conteúdo do documento."""
    p = Path(source) if source and not source.startswith("(") else None
    size = None
    try:
        size = round(p.stat().st_size / 1024) if p is not None and p.is_file() else None
    except OSError:
        pass
    _ERRORS.append({"when": dt.datetime.now().strftime("%H:%M:%S"), "name": p.name if p else source,
                    "ext": p.suffix.lower() if p else "", "size_kb": size, "message": _redact(message),
                    "tb": _redact(tb.rstrip()), "context": _clean_context(context or {})})


def _clean_context(ctx: dict) -> dict:
    """Configuração da conversão sem caminhos de pastas (só valores de opções)."""
    out = {}
    for k, v in ctx.items():
        if isinstance(v, dict):
            v = _clean_context(v)
        elif isinstance(v, str) and ("\\" in v or "/" in v) and k not in ("ocr_lang",):
            v = "<caminho omitido>"
        out[k] = v
    return out


def _memory_gb() -> str:
    try:
        if os.name == "nt":
            import ctypes

            class MS(ctypes.Structure):
                _fields_ = [("dwLength", ctypes.c_ulong), ("dwMemoryLoad", ctypes.c_ulong),
                            ("ullTotalPhys", ctypes.c_ulonglong), ("ullAvailPhys", ctypes.c_ulonglong),
                            ("ullTotalPageFile", ctypes.c_ulonglong), ("ullAvailPageFile", ctypes.c_ulonglong),
                            ("ullTotalVirtual", ctypes.c_ulonglong), ("ullAvailVirtual", ctypes.c_ulonglong),
                            ("ullAvailExtendedVirtual", ctypes.c_ulonglong)]
            m = MS()
            m.dwLength = ctypes.sizeof(MS)
            ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(m))
            return f"{m.ullTotalPhys / 1024 ** 3:.1f} GB (livre: {m.ullAvailPhys / 1024 ** 3:.1f} GB)"
        if Path("/proc/meminfo").exists():
            info = dict(line.split(":", 1) for line in Path("/proc/meminfo").read_text().splitlines() if ":" in line)
            total = int(info["MemTotal"].split()[0]) / 1024 ** 2
            free = int(info.get("MemAvailable", "0 kB").split()[0]) / 1024 ** 2
            return f"{total:.1f} GB (livre: {free:.1f} GB)"
        if sys.platform == "darwin":
            import subprocess

            total = int(subprocess.run(["sysctl", "-n", "hw.memsize"], capture_output=True, text=True).stdout)
            return f"{total / 1024 ** 3:.1f} GB"
    except Exception:  # noqa: BLE001
        pass
    return "desconhecida"


def system_info() -> list[str]:
    """Informações do computador úteis para o suporte (sem nome de usuário ou de computador)."""
    import locale

    lines = [f"Sistema: {platform.platform(terse=False)}",
             f"Processador: {platform.machine()} — {os.cpu_count() or '?'} núcleo(s)",
             f"Memória: {_memory_gb()}",
             f"Idioma do sistema: {locale.getlocale()[0] or '?'}"]
    try:
        from PySide6 import __version__ as pyside
        from PySide6.QtGui import QGuiApplication

        lines.append(f"Qt/PySide6: {pyside}")
        app = QGuiApplication.instance()
        scr = app.primaryScreen() if app is not None else None
        if scr is not None:
            g = scr.geometry()
            lines.append(f"Tela: {g.width()}×{g.height()} (escala {scr.devicePixelRatio():g}×)")
    except Exception:  # noqa: BLE001
        pass
    return lines


def _render_errors(hide_names: bool) -> list[str]:
    if not _ERRORS:
        return ["(nenhum)"]
    out, aliases = [], {}
    for e in _ERRORS:
        name = e["name"] or "?"
        if hide_names and not name.startswith("("):
            name = aliases.setdefault(name, f"arquivo{len(aliases) + 1}{e['ext']}")
        size = f", {e['size_kb']} KB" if e.get("size_kb") is not None else ""
        out.append(f"### [{e['when']}] {name}{size}")
        msg = e["message"]
        if hide_names:
            for real, alias in aliases.items():
                msg = msg.replace(real, alias)
        out.append(msg)
        if e["context"]:
            out.append("Configuração usada nesta conversão:")
            for k, v in e["context"].items():
                out.append(f"- {k}: {v}")
        if e["tb"]:
            out += ["Detalhes técnicos:", e["tb"]]
        out.append("")
    return out


_SAFE_PREFIXES = ("mode", "engine", "opt/", "fix/", "out/images", "out/profile", "out/frontmatter",
                  "out/describe", "naming/template", "naming/ext", "naming/safe", "naming/conflict",
                  "queue/", "theme", "ui/", "export/fmt", "export/template", "watch/enabled")


def report_text(settings=None, hide_names: bool = False) -> str:
    """Texto do relatório. `hide_names`: troca os nomes dos arquivos por arquivo1.pdf, arquivo2.docx…"""
    from . import __version__
    from .edition import label

    lines = ["# Relatório de erro do Markinho", "",
             f"Gerado em: {dt.datetime.now():%d/%m/%Y %H:%M}",
             f"Versão: {__version__} — edição {label()}",
             f"Python: {platform.python_version()}{' (instalador)' if getattr(sys, 'frozen', False) else ''}"]
    lines += system_info() + [""]
    try:
        from .engines import ENGINES

        lines.append("## Motores")
        for e in ENGINES.values():
            ok, why = e.available()
            lines.append(f"- {e.id}: {'disponível' if ok else 'indisponível'}" + ("" if ok else f" ({why[:120]})"))
        from .ocr import describe_status

        lines += ["", f"OCR: {describe_status()}", ""]
    except Exception as exc:  # noqa: BLE001
        lines += [f"(não foi possível listar os motores: {exc})", ""]
    if settings is not None:
        lines.append("## Configurações (sem pastas e arquivos)")
        for k in sorted(settings.allKeys()):
            if k.startswith(_SAFE_PREFIXES):
                lines.append(f"- {k} = {settings.value(k)}")
        lines.append("")
    lines.append("## Erros recentes (desde que o Markinho foi aberto)")
    lines += _render_errors(hide_names)
    lines += ["## Registros recentes"]
    logs = [_redact(x) for x in list(_LOG)[-150:]]
    if hide_names:
        for e in _ERRORS:
            if e["name"] and not e["name"].startswith("("):
                logs = [x.replace(e["name"], "<arquivo>") for x in logs]
    lines += logs or ["(nenhum)"]
    lines += ["", "— O conteúdo dos seus documentos não está neste relatório. Nada foi enviado: confira o texto e "
                  "decida se quer mandá-lo ao suporte."]
    return "\n".join(lines) + "\n"
