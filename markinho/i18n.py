# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 dontstopbelieve — Markinho
"""Idiomas da interface.

O texto original (português do Brasil) é a própria chave: ``tr("Converter")``. As traduções ficam em
``markinho/locale/<idioma>.json`` (``{"Converter": "Convert", ...}``). Texto sem tradução aparece em
português — o programa nunca quebra por falta de tradução.

O idioma é decidido uma vez, na primeira importação, nesta ordem: variável ``MARKINHO_LANG``,
configuração “ui/lang” (Configurações > Aparência), idioma do sistema (português → pt; espanhol → es; outros → en).
Trocar de idioma vale ao abrir o programa de novo.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

LANGUAGES = [("auto", "Automático (idioma do sistema)"), ("pt", "Português (Brasil)"), ("en", "English"), ("es", "Español")]
_DIR = Path(__file__).resolve().parent / "locale"


def _detect() -> str:
    env = (os.environ.get("MARKINHO_LANG") or "").strip().lower()
    if env:
        return env[:2]
    try:
        from PySide6.QtCore import QLocale, QSettings

        saved = str(QSettings("Markinho", "Markinho").value("ui/lang", "auto") or "auto")
        if saved != "auto":
            return saved[:2]
        sys_lang = QLocale.system().name().lower()[:2]
        return sys_lang if sys_lang in ("pt", "es") else "en"
    except Exception:  # noqa: BLE001
        return "pt"


def _load(lang: str) -> dict[str, str]:
    if lang == "pt":
        return {}
    try:
        return json.loads((_DIR / f"{lang}.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


LANG = _detect()
_CATALOG = _load(LANG)


def tr(text: str) -> str:
    """Traduz `text` (escrito em português) para o idioma da interface."""
    return _CATALOG.get(text, text) if _CATALOG else text


def num(n: int) -> str:
    """Número com separador de milhar do idioma: 1.023 (português, espanhol) ou 1,023 (inglês)."""
    s = f"{n:,}"
    return s.replace(",", ".") if LANG in ("pt", "es") else s


def language() -> str:
    return LANG


def set_language_for_tests(lang: str) -> None:
    """Só para testes: troca o idioma em tempo de execução (textos já criados não mudam)."""
    global LANG, _CATALOG
    LANG, _CATALOG = lang, _load(lang)
