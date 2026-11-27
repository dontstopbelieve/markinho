# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 dontstopbelieve — Markinho
"""Só as tabelas: tira as tabelas do Markdown convertido e grava numa planilha (Excel) ou em CSV.

- Lê tabelas Markdown (``| a | b |``) e tabelas HTML (as de células mescladas, com rowspan/colspan).
- Excel: uma aba por tabela + uma aba “Índice” com o título (o título acima da tabela ou “Tabela 3 – …”),
  a página (quando o PDF tem marcas de página) e o tamanho. Cabeçalho em negrito, filtro e 1ª linha fixa;
  células mescladas continuam mescladas.
- Números viram números de verdade (“1.234,56”, “12,5%”, “R$ 10,00”), para somar no Excel. Códigos com
  zero à esquerda (“007”), CPF, datas e telefones continuam como texto.
- Segurança: texto que começa com “=”, “+”, “-”, “@” nunca vira fórmula (documentos podem ser maliciosos).
"""
from __future__ import annotations

import csv
import io
import re
from dataclasses import dataclass, field
from pathlib import Path

from .i18n import language, tr

MAX_CELLS = 200_000          # proteção: tabela absurda (documento preparado) não trava o programa
MAX_SPAN = 1000


@dataclass
class TableData:
    title: str
    rows: list[list[str]]
    page: int | None = None
    merges: list[tuple[int, int, int, int]] = field(default_factory=list)   # (linha1, col1, linha2, col2), 0-based

    @property
    def width(self) -> int:
        return max((len(r) for r in self.rows), default=0)


_SEP = re.compile(r"^\s*\|?\s*:?-{3,}:?\s*(\|\s*:?-{3,}:?\s*)*\|?\s*$")
_CAPTION = re.compile(r"^\s*(\*\*|_)?\s*(tabela|table|tabla|quadro|tab\.)\s*[\dIVXLC]+\b", re.I)
_PAGE = re.compile(r"<!--\s*(?:página|page|pagina)\s+(\d+)\s*-->", re.I)
_FENCE = re.compile(r"^\s{0,3}(```|~~~)")


def _clean(cell: str) -> str:
    cell = re.sub(r"<br\s*/?>", "\n", cell, flags=re.I)
    cell = cell.replace("\\|", "|")
    cell = re.sub(r"(\*\*|__)(.+?)\1", r"\2", cell)          # negrito
    cell = re.sub(r"`([^`]*)`", r"\1", cell)
    return cell.strip()


def _split_row(line: str) -> list[str]:
    line = line.strip()
    if line.startswith("|"):
        line = line[1:]
    if line.endswith("|") and not line.endswith("\\|"):
        line = line[:-1]
    return [_clean(c) for c in re.split(r"(?<!\\)\|", line)]


def _html_table(fragment: str) -> tuple[list[list[str]], list[tuple[int, int, int, int]]]:
    """Tabela HTML → grade (células mescladas repetidas só na 1ª posição) + lista de mesclagens."""
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(fragment, "html.parser")
    grid: dict[tuple[int, int], str] = {}
    merges = []
    taken: set[tuple[int, int]] = set()
    for r, tr_ in enumerate(soup.find_all("tr")):
        c = 0
        for cell in tr_.find_all(["td", "th"]):
            while (r, c) in taken:
                c += 1
            try:
                rs = max(1, min(int(cell.get("rowspan", 1) or 1), MAX_SPAN))
                cs = max(1, min(int(cell.get("colspan", 1) or 1), MAX_SPAN))
            except ValueError:
                rs = cs = 1
            if len(taken) + rs * cs > MAX_CELLS:
                break
            text = _clean(cell.get_text("\n"))
            grid[(r, c)] = text
            for dr in range(rs):
                for dc in range(cs):
                    taken.add((r + dr, c + dc))
            if rs > 1 or cs > 1:
                merges.append((r, c, r + rs - 1, c + cs - 1))
            c += cs
    if not taken:
        return [], []
    nr = max(r for r, _ in taken) + 1
    nc = max(c for _, c in taken) + 1
    rows = [[grid.get((r, c), "") for c in range(nc)] for r in range(nr)]
    return rows, merges


def extract_tables(md: str) -> list[TableData]:
    """Todas as tabelas do Markdown, na ordem, com título e página quando houver."""
    lines = md.splitlines()
    out: list[TableData] = []
    heading = ""
    caption = ""
    page: int | None = None
    in_code = False
    i = 0
    while i < len(lines):
        line = lines[i]
        if _FENCE.match(line):
            in_code = not in_code
            i += 1
            continue
        if in_code:
            i += 1
            continue
        if m := _PAGE.search(line):
            page = int(m.group(1))
        stripped = line.strip()
        if stripped.startswith("#"):
            heading = stripped.lstrip("#").strip()
            caption = ""
        elif _CAPTION.match(stripped) and len(stripped) < 200:
            caption = re.sub(r"[*_]", "", stripped).strip()
        if stripped.startswith("|") and i + 1 < len(lines) and _SEP.match(lines[i + 1]):
            block = [line]
            j = i + 2
            while j < len(lines) and lines[j].strip().startswith("|"):
                block.append(lines[j])
                j += 1
            rows = [_split_row(block[0])] + [_split_row(x) for x in block[1:]]
            out.append(TableData(caption or heading, rows[: MAX_CELLS // max(1, len(rows[0]))], page))
            caption = ""
            i = j
            continue
        if stripped.lower().startswith("<table"):
            j = i
            buf = []
            while j < len(lines) and len(buf) < 20000:
                buf.append(lines[j])
                if "</table>" in lines[j].lower():
                    break
                j += 1
            rows, merges = _html_table("\n".join(buf))
            if rows:
                out.append(TableData(caption or heading, rows, page, merges))
                caption = ""
            i = j + 1
            continue
        i += 1
    for k, t in enumerate(out, 1):
        if not t.title:
            t.title = tr("Tabela {0}").format(k)
    return out


# --------------------------------------------------------------------------- #
# Números
# --------------------------------------------------------------------------- #
_CURRENCY = re.compile(r"^(R\$|US\$|\$|€|£)\s*")
_DANGER = ("=", "+", "-", "@", "\t", "\r")


def to_number(text: str, decimal_comma: bool | None = None):
    """“1.234,56” → 1234.56; “12,5%” → 0.125; “R$ 10” → 10. Devolve (valor, formato) ou None se não for número.
    `decimal_comma`: vírgula é decimal? (padrão: pelo idioma — português/espanhol sim, inglês não)."""
    s = text.strip().replace(" ", " ")
    if not s or len(s) > 40:
        return None
    if decimal_comma is None:
        decimal_comma = language() in ("pt", "es")
    fmt = "General"
    neg = False
    if s.startswith("(") and s.endswith(")"):                # (1.234) = negativo, em balanços
        s, neg = s[1:-1].strip(), True
    if m := _CURRENCY.match(s):
        s = s[m.end():]
        fmt = "#,##0.00"
    pct = s.endswith("%")
    if pct:
        s = s[:-1].strip()
    if s.startswith("-"):
        s, neg = s[1:].strip(), not neg
    s = s.replace(" ", "")
    if not re.fullmatch(r"\d([\d.,]*\d)?", s) or re.match(r"0\d", s):    # zero à esquerda: código, não número
        return None
    if "." in s and "," in s:                                  # os dois: o último é o decimal
        dec = "," if s.rfind(",") > s.rfind(".") else "."
        thou = "." if dec == "," else ","
    elif "," in s or "." in s:
        ch = "," if "," in s else "."
        grouped = re.fullmatch(r"\d{1,3}(" + re.escape(ch) + r"\d{3})+", s)
        if s.count(ch) > 1:                                    # 1.234.567: só pode ser milhar
            if not grouped:
                return None
            dec, thou = None, ch
        elif grouped and ch == ("." if decimal_comma else ","):   # 1.234 (pt) ou 1,234 (en) = milhar
            dec, thou = None, ch
        else:
            dec, thou = ch, None
    else:
        dec = thou = None
    intpart, _, frac = s.partition(dec) if dec else (s, "", "")
    if dec and s.count(dec) != 1:
        return None
    if thou:
        if not re.fullmatch(r"\d{1,3}(" + re.escape(thou) + r"\d{3})*", intpart):
            return None
        intpart = intpart.replace(thou, "")
    if not intpart.isdigit() or (dec and not frac.isdigit()):
        return None
    value = float(f"{intpart}.{frac}") if dec else int(intpart)
    if neg:
        value = -value
    if pct:
        value = value / 100
        fmt = "0.##%"
    return value, fmt


def _safe_text(text: str) -> str:
    """Para CSV: texto que o Excel leria como fórmula ganha um apóstrofo na frente."""
    return "'" + text if text.startswith(_DANGER) else text


# --------------------------------------------------------------------------- #
# Gravação
# --------------------------------------------------------------------------- #
def _sheet_name(base: str, used: set[str]) -> str:
    name = re.sub(r"[\[\]:*?/\\]", " ", base).strip()[:31] or "Tabela"
    out, k = name, 2
    while out.lower() in used:
        suffix = f" ({k})"
        out, k = name[: 31 - len(suffix)] + suffix, k + 1
    used.add(out.lower())
    return out


def write_xlsx(tables: list[TableData], target: Path, source: str = "") -> None:
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Font
    from openpyxl.utils import get_column_letter

    wb = Workbook()
    idx = wb.active
    idx.title = tr("Índice")[:31]
    used = {idx.title.lower()}
    bold = Font(bold=True)
    head = [tr("Nº"), tr("Aba"), tr("Título"), tr("Página"), tr("Linhas"), tr("Colunas")]
    if source:
        idx.append([tr("Tabelas extraídas pelo Markinho de: {0}").format(source)])
        idx["A1"].font = bold
        idx.append([])
    idx.append(head)
    for c in idx[idx.max_row]:
        c.font = bold
    for n, t in enumerate(tables, 1):
        ws = wb.create_sheet(_sheet_name(tr("Tabela {0}").format(n), used))
        for r, row in enumerate(t.rows, 1):
            for c, text in enumerate(row, 1):
                cell = ws.cell(row=r, column=c)
                num = to_number(text) if r > 1 else None
                if num is not None:
                    cell.value, cell.number_format = num[0], num[1]
                else:
                    cell.value = text
                    cell.data_type = "s"             # nunca fórmula, mesmo começando com “=”
                    if "\n" in text:
                        cell.alignment = Alignment(wrap_text=True, vertical="top")
                if r == 1:
                    cell.font = bold
        for r1, c1, r2, c2 in t.merges:
            ws.merge_cells(start_row=r1 + 1, start_column=c1 + 1, end_row=r2 + 1, end_column=c2 + 1)
        if t.rows:
            ws.freeze_panes = "A2"
            if not t.merges:
                ws.auto_filter.ref = f"A1:{get_column_letter(t.width)}{len(t.rows)}"
        for c in range(1, t.width + 1):
            longest = max((len(str(r[c - 1]).split("\n")[0]) for r in t.rows if len(r) >= c), default=8)
            ws.column_dimensions[get_column_letter(c)].width = min(60, max(8, longest + 2))
        row = [n, ws.title, t.title, t.page or "", len(t.rows) - 1, t.width]
        idx.append(row)
        link = idx.cell(row=idx.max_row, column=2)
        link.hyperlink = f"#'{ws.title}'!A1"
        link.style = "Hyperlink"
        idx.cell(row=idx.max_row, column=3).data_type = "s"
    for col, w in zip("ABCDEF", (5, 14, 60, 8, 8, 8)):
        idx.column_dimensions[col].width = w
    wb.save(target)


def write_csv(tables: list[TableData], target: Path) -> None:
    """Uma tabela: CSV simples. Várias: uma após a outra, separadas por uma linha em branco e o título.
    Separador “;” em português/espanhol (o Excel desses idiomas espera ponto e vírgula), “,” em inglês."""
    sep = ";" if language() in ("pt", "es") else ","
    buf = io.StringIO()
    w = csv.writer(buf, delimiter=sep, lineterminator="\r\n")
    for k, t in enumerate(tables):
        if len(tables) > 1:
            if k:
                w.writerow([])
            w.writerow([_safe_text(t.title)])
        for row in t.rows:
            w.writerow([text if to_number(text) is not None else _safe_text(text) for text in row])
    Path(target).write_text(buf.getvalue(), encoding="utf-8-sig")       # com BOM: o Excel acerta os acentos


def export_tables(md: str, target: Path, kind: str, source: str = "") -> int:
    # tabelas de verdade: 2+ colunas e pelo menos uma linha além do cabeçalho (pedaços de figura ficam de fora)
    tables = [t for t in extract_tables(md) if t.width >= 2 and len(t.rows) >= 2]
    if not tables:
        raise RuntimeError(tr("Nenhuma tabela encontrada neste documento."))
    if kind == "xlsx":
        write_xlsx(tables, Path(target), source)
    else:
        write_csv(tables, Path(target))
    return len(tables)
