"""Só as tabelas → Excel/CSV: leitura das tabelas do Markdown, números, mesclagens e segurança."""
import csv
from pathlib import Path

import pytest

from markinho import i18n
from markinho.exporter import export
from markinho.tables import extract_tables, to_number

MD = """# Relatório

Texto antes.

**Tabela 1 – Vendas por região**

| Região | Receita | Variação |
|---|---|---|
| Norte | 1.234,56 | 12,5% |
| Sul \\| Sudeste | R$ 2.000,00 | -3,0% |
| Código | 007 | =HYPERLINK("http://mal") |

<!-- Página 4 -->

## Equipe

<table><tr><th>Área</th><th colspan="2">Pessoas</th></tr>
<tr><td rowspan="2">TI</td><td>Ana</td><td>Bia</td></tr>
<tr><td>Caio</td><td>Duda</td></tr></table>

```
| isto | é código |
|---|---|
```
"""


def test_le_tabelas_com_titulo_pagina_e_mesclagem():
    t = extract_tables(MD)
    assert len(t) == 2
    assert t[0].title == "Tabela 1 – Vendas por região" and t[0].page is None
    assert t[0].rows[2][0] == "Sul | Sudeste"
    assert t[1].title == "Equipe" and t[1].page == 4
    assert t[1].rows[0] == ["Área", "Pessoas", ""] and t[1].rows[2][0] == ""
    assert (0, 1, 0, 2) in t[1].merges and (1, 0, 2, 0) in t[1].merges


@pytest.mark.parametrize("text,dc,expected", [
    ("1.234,56", True, 1234.56), ("1,234.56", False, 1234.56), ("1.234", True, 1234), ("1.234", False, 1.234),
    ("12,5%", True, 0.125), ("R$ 10,00", True, 10.0), ("(1.234)", True, -1234), ("-3", True, -3),
    ("007", True, None), ("123.456.789-00", True, None), ("12/05/2024", True, None), ("1.2.3", True, None),
    ("+55 11 9999", True, None), ("abc", True, None), ("1.234.567", False, 1234567),
])
def test_numeros(text, dc, expected):
    got = to_number(text, dc)
    assert (got[0] if got else None) == expected


def test_excel(tmp_path):
    from openpyxl import load_workbook

    target = tmp_path / "t.xlsx"
    export(MD, target, "xlsx", {"source": "relatorio.pdf"})
    wb = load_workbook(target)
    assert wb.sheetnames == ["Índice", "Tabela 1", "Tabela 2"]
    ws = wb["Tabela 1"]
    assert ws["B2"].value == 1234.56 and ws["C2"].value == 0.125 and ws["B3"].value == 2000.0
    assert ws["B4"].value == "007"                                # zero à esquerda: texto
    assert ws["C4"].value == '=HYPERLINK("http://mal")' and ws["C4"].data_type == "s"   # nunca fórmula
    assert ws["A1"].font.bold and ws.freeze_panes == "A2"
    assert "B1:C1" in {str(r) for r in wb["Tabela 2"].merged_cells.ranges}
    idx = wb["Índice"]
    titles = [c.value for c in idx["C"]]
    assert "Tabela 1 – Vendas por região" in titles and "relatorio.pdf" in idx["A1"].value


def test_csv_com_varias_tabelas_e_protecao(tmp_path):
    target = tmp_path / "t.csv"
    export(MD, target, "csv")
    raw = target.read_bytes()
    assert raw.startswith(b"\xef\xbb\xbf")                       # BOM: o Excel acerta os acentos
    rows = list(csv.reader(target.read_text(encoding="utf-8-sig").splitlines(), delimiter=";"))
    assert rows[0] == ["Tabela 1 – Vendas por região"]
    flat = [c for r in rows for c in r]
    assert "'=HYPERLINK(\"http://mal\")" in flat                  # apóstrofo: o Excel não executa
    assert "-3,0%" in flat and "'-3,0%" not in flat               # número negativo não é “fórmula”
    assert "Equipe" in flat


def test_csv_em_ingles_usa_virgula(tmp_path):
    try:
        i18n.set_language_for_tests("en")
        target = tmp_path / "t.csv"
        export("| a | b |\n|---|---|\n| 1 | 2 |\n", target, "csv")
        assert target.read_text(encoding="utf-8-sig").splitlines()[0] == "a,b"
    finally:
        i18n.set_language_for_tests("pt")


def test_sem_tabelas_avisa(tmp_path):
    with pytest.raises(RuntimeError, match="Nenhuma tabela"):
        export("# Só texto\n\nNada aqui.", tmp_path / "x.xlsx", "xlsx")


def test_tabela_html_absurda_nao_trava():
    md = '<table><tr><td rowspan="999999999" colspan="999999">x</td><td>y</td></tr></table>'
    import time

    start = time.time()
    t = extract_tables(md)
    assert time.time() - start < 2 and all(len(x.rows) <= 1000 for x in t)
    ok = extract_tables('<table><tr><td rowspan="5000">x</td><td>y</td></tr><tr><td>z</td></tr></table>')
    assert ok and len(ok[0].rows) <= 1000                          # rowspan limitado


def test_terminal_tabelas_para_excel(tmp_path, monkeypatch):
    import shutil

    from markinho.__main__ import cli

    monkeypatch.chdir(tmp_path)
    src = tmp_path / "planilha.md"
    src.write_text(MD, encoding="utf-8")
    assert cli([str(src), "-t", "xlsx", "-o", str(tmp_path / "out.xlsx")]) == 0
    assert (tmp_path / "out.xlsx").is_file()
