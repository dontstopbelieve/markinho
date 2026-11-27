# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 dontstopbelieve — Markinho
"""Lembrete de atualização — sem internet.

O Markinho nunca procura atualizações sozinho (nada sai do computador). Em vez disso, cerca de 2 meses depois
da data da versão instalada (e depois a cada 2 meses), ele lembra a pessoa de conferir a página de versões
no GitHub. A página só é aberta se ela clicar. “Não lembrar mais” desliga o lembrete; Ajuda > Procurar
atualizações… continua disponível.
"""
from __future__ import annotations

import datetime as dt
from pathlib import Path

RELEASES_URL = "https://github.com/dontstopbelieve/markinho/releases"
INTERVAL_DAYS = 60


def build_date() -> dt.date | None:
    """Data em que o instalador foi gerado (gravada no build); None rodando pelo código-fonte."""
    try:
        text = (Path(__file__).resolve().parent / "resources" / "build-date.txt").read_text(encoding="utf-8")
        return dt.date.fromisoformat(text.strip())
    except (OSError, ValueError):
        return None


def _date(settings, key: str) -> dt.date | None:
    try:
        return dt.date.fromisoformat(str(settings.value(key, "") or ""))
    except ValueError:
        return None


def due(settings, today: dt.date | None = None) -> bool:
    """Está na hora de lembrar? Conta a partir da data da versão (ou do 1º uso) e do último lembrete."""
    today = today or dt.date.today()
    if settings.value("updates/never", False, type=bool):
        return False
    first = _date(settings, "updates/first_seen")
    if first is None:
        settings.setValue("updates/first_seen", today.isoformat())
        first = today
    base = _date(settings, "updates/last_reminder") or build_date() or first
    # nunca na primeira semana de uso (mesmo que a versão instalada já seja antiga)
    return (today - base).days >= INTERVAL_DAYS and (today - first).days >= 7


def snooze(settings, today: dt.date | None = None) -> None:
    settings.setValue("updates/last_reminder", (today or dt.date.today()).isoformat())


def never(settings) -> None:
    settings.setValue("updates/never", True)
