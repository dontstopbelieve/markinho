# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 dontstopbelieve — Markinho
"""Relatório do lote: o que foi convertido, avisos e erros, em planilha (CSV) ou página (HTML)."""
from __future__ import annotations

from .i18n import language, tr

import csv
import datetime as dt
import html
from pathlib import Path

COLUMNS = [("arquivo", tr("Arquivo")), ("pasta", tr("Pasta")), ("situacao", tr("Situação")), ("motor", tr("Motor")),
           ("caracteres", tr("Caracteres")), ("imagens", tr("Imagens")), ("segundos", tr("Segundos")),
           ("revisar", tr("Páginas a revisar")), ("avisos", tr("Avisos")), ("erro", tr("Erro"))]
# situação de cada linha: o código fica em "estado" (não depende do idioma); "situacao" é o texto visível
STATES = {"ok": tr("Convertido"), "aviso": tr("Convertido com avisos"), "erro": tr("Erro"),
          "fila": tr("Na fila"), "convertendo": tr("Convertendo")}


def row(path: str, result=None, error: str = "", queued: bool = False) -> dict:
    p = Path(path)
    r = {"arquivo": p.name, "pasta": str(p.parent), "situacao": "", "motor": "", "caracteres": "",
         "imagens": "", "segundos": "", "revisar": "", "avisos": "", "erro": error}
    if error:
        r["estado"] = "erro"
    elif result is not None:
        from .core import is_alert

        warn = any(is_alert(w) for w in result.warnings) or bool(result.review_pages)
        r.update(estado="aviso" if warn else "ok", motor=result.converter,
                 caracteres=len(result.markdown), imagens=len(result.assets), segundos=f"{result.seconds:.2f}",
                 revisar=", ".join(map(str, result.review_pages)), avisos=" | ".join(result.warnings))
    else:
        r["estado"] = "fila" if queued else "convertendo"
    r["situacao"] = STATES[r["estado"]]
    return r


def summary(rows: list[dict]) -> str:
    ok = sum(r.get("estado") in ("ok", "aviso") for r in rows)
    warn = sum(r.get("estado") == "aviso" for r in rows)
    bad = sum(r.get("estado") == "erro" for r in rows)
    return tr('{0} arquivo(s): {1} convertido(s) ({2} com avisos), {3} com erro.').format(len(rows), ok, warn, bad)


def to_csv(rows: list[dict], path: Path) -> None:
    """CSV com “;” e BOM: abre direto no Excel em português."""
    with open(path, "w", newline="", encoding="utf-8-sig") as fh:
        w = csv.writer(fh, delimiter=";")
        w.writerow([label for _, label in COLUMNS])
        for r in rows:
            w.writerow([r.get(k, "") for k, _ in COLUMNS])


def to_html(rows: list[dict], path: Path) -> None:
    head = "".join(f"<th>{html.escape(label)}</th>" for _, label in COLUMNS)
    body = []
    for r in rows:
        cls = {"erro": "erro", "aviso": "aviso"}.get(r.get("estado", ""), "")
        body.append(f'<tr class="{cls}">' + "".join(f"<td>{html.escape(str(r.get(k, '')))}</td>"
                                                   for k, _ in COLUMNS) + "</tr>")
    when = dt.datetime.now().strftime("%d/%m/%Y %H:%M")
    path.write_text(
        f"<!DOCTYPE html><html lang='{'pt-BR' if language() == 'pt' else language()}'><head><meta charset='utf-8'>"
        f"<title>{tr('Relatório do lote')} — Markinho</title>"
        "<style>body{font-family:system-ui,sans-serif;margin:2em}table{border-collapse:collapse;font-size:13px}"
        "th,td{border:1px solid #ccc;padding:4px 8px;text-align:left;vertical-align:top}th{background:#f0f2f0}"
        "tr.erro td{background:#fde8e8}tr.aviso td{background:#fff7d6}</style></head><body>"
        f"<h1>{tr('Relatório do lote')}</h1><p>Markinho — {when}. {html.escape(summary(rows))}</p>"
        f"<table><thead><tr>{head}</tr></thead><tbody>{''.join(body)}</tbody></table></body></html>",
        encoding="utf-8")
