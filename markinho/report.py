# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 dontstopbelieve — Markinho
"""Relatório do lote: o que foi convertido, avisos e erros, em planilha (CSV) ou página (HTML)."""
from __future__ import annotations

import csv
import datetime as dt
import html
from pathlib import Path

COLUMNS = [("arquivo", "Arquivo"), ("pasta", "Pasta"), ("situacao", "Situação"), ("motor", "Motor"),
           ("caracteres", "Caracteres"), ("imagens", "Imagens"), ("segundos", "Segundos"),
           ("revisar", "Páginas a revisar"), ("avisos", "Avisos"), ("erro", "Erro")]


def row(path: str, result=None, error: str = "", queued: bool = False) -> dict:
    p = Path(path)
    r = {"arquivo": p.name, "pasta": str(p.parent), "situacao": "", "motor": "", "caracteres": "",
         "imagens": "", "segundos": "", "revisar": "", "avisos": "", "erro": error}
    if error:
        r["situacao"] = "Erro"
    elif result is not None:
        from .core import is_alert

        warn = any(is_alert(w) for w in result.warnings) or bool(result.review_pages)
        r.update(situacao="Convertido com avisos" if warn else "Convertido", motor=result.converter,
                 caracteres=len(result.markdown), imagens=len(result.assets), segundos=f"{result.seconds:.2f}",
                 revisar=", ".join(map(str, result.review_pages)), avisos=" | ".join(result.warnings))
    else:
        r["situacao"] = "Na fila" if queued else "Convertendo"
    return r


def summary(rows: list[dict]) -> str:
    ok = sum(r["situacao"].startswith("Convertido") for r in rows)
    warn = sum(r["situacao"] == "Convertido com avisos" for r in rows)
    bad = sum(r["situacao"] == "Erro" for r in rows)
    return f"{len(rows)} arquivo(s): {ok} convertido(s) ({warn} com avisos), {bad} com erro."


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
        cls = {"Erro": "erro", "Convertido com avisos": "aviso"}.get(r["situacao"], "")
        body.append(f'<tr class="{cls}">' + "".join(f"<td>{html.escape(str(r.get(k, '')))}</td>"
                                                   for k, _ in COLUMNS) + "</tr>")
    when = dt.datetime.now().strftime("%d/%m/%Y %H:%M")
    path.write_text(
        "<!DOCTYPE html><html lang='pt-BR'><head><meta charset='utf-8'><title>Relatório do lote — Markinho</title>"
        "<style>body{font-family:system-ui,sans-serif;margin:2em}table{border-collapse:collapse;font-size:13px}"
        "th,td{border:1px solid #ccc;padding:4px 8px;text-align:left;vertical-align:top}th{background:#f0f2f0}"
        "tr.erro td{background:#fde8e8}tr.aviso td{background:#fff7d6}</style></head><body>"
        f"<h1>Relatório do lote</h1><p>Markinho — {when}. {html.escape(summary(rows))}</p>"
        f"<table><thead><tr>{head}</tr></thead><tbody>{''.join(body)}</tbody></table></body></html>",
        encoding="utf-8")
