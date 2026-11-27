# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 dontstopbelieve — Markinho
"""Colunas achadas pelas palavras (2, 3 ou mais; corredor estreito) e cabeçalhos/rodapés de uma página só."""
from pathlib import Path

import pytest

from markinho.pdf import column_rivers, river_order, strip_page_furniture

SIZE = 9.0


def _col_words(x0: float, width: float, top: float, rows: int, tag: str, gap_rows: tuple = ()) -> list[dict]:
    """Palavras de uma coluna de texto corrido: 6 palavras por linha, largura `width`."""
    out = []
    for r in range(rows):
        if r in gap_rows:
            continue
        y = top + r * 12
        step = width / 6
        for k in range(6):
            out.append({"text": f"{tag}{r}w{k}", "x0": x0 + k * step, "x1": x0 + k * step + step - 3,
                        "top": y, "bottom": y + SIZE, "size": SIZE, "upright": True})
    return out


def _line(text: str, x0: float, x1: float, top: float, size: float = SIZE) -> dict:
    return {"kind": "line", "text": text, "x0": x0, "x1": x1, "top": top, "bottom": top + size, "size": size}


def test_tres_colunas_de_jornal_com_corredor_estreito():
    W = 612
    words = (_col_words(40, 170, 100, 20, "A") + _col_words(216, 170, 100, 20, "B")
             + _col_words(392, 170, 100, 20, "C"))
    rivers = column_rivers(words, W)
    assert len(rivers) == 2
    xs = sorted(r[0] for r in rivers)
    assert 207 < xs[0] < 217 and 383 < xs[1] < 393


def test_texto_de_uma_coluna_e_lista_estreita_nao_viram_colunas():
    W = 612
    assert column_rivers(_col_words(72, 460, 100, 30, "T"), W) == []
    # horário / rótulo: valor — vão constante, mas um lado é estreito (não é coluna)
    lista = []
    for r in range(12):
        y = 100 + r * 12
        lista.append({"text": "10.40", "x0": 72, "x1": 100, "top": y, "bottom": y + SIZE, "size": SIZE})
        lista.append({"text": "–", "x0": 103, "x1": 108, "top": y, "bottom": y + SIZE, "size": SIZE})
        lista.append({"text": "11.20", "x0": 111, "x1": 139, "top": y, "bottom": y + SIZE, "size": SIZE})
        for k in range(5):
            lista.append({"text": f"Nome{k}", "x0": 200 + k * 60, "x1": 250 + k * 60, "top": y,
                          "bottom": y + SIZE, "size": SIZE})
    assert column_rivers(lista, W) == []


def test_ordem_pelos_corredores_com_titulo_atravessando():
    W = 612
    rivers = [(306.0, 120.0, 400.0)]
    blocks = [_line("Título que atravessa a página", 72, 540, 90, 16)]
    for r in range(10):
        blocks.append(_line(f"esquerda {r}", 72, 296, 120 + r * 12))
        blocks.append(_line(f"direita {r}", 316, 540, 120 + r * 12))
    blocks.append(_line("Rodapé do artigo que atravessa", 72, 540, 420))
    out = [b["text"] for b in river_order(blocks, W, rivers)]
    assert out[0].startswith("Título")
    assert out[1:11] == [f"esquerda {r}" for r in range(10)]
    assert out[11:21] == [f"direita {r}" for r in range(10)]
    assert out[-1].startswith("Rodapé")


def test_coluna_mais_comprida_que_a_outra_continua_na_ordem():
    W = 612
    words = _col_words(40, 250, 100, 20, "E") + _col_words(320, 250, 100, 12, "D")
    rivers = column_rivers(words, W)
    assert len(rivers) == 1
    t, b = rivers[0][1], rivers[0][2]
    assert t <= 100 and b >= 100 + 19 * 12            # vai até o fim da coluna mais comprida


def _page(rows, H=800.0):
    blocks = [_line(f"Texto do corpo número {k} com bastante conteúdo de verdade", 72, 540, 150 + k * 14)
              for k in range(30)]
    for text, x0, x1, top, size in rows:
        blocks.append(_line(text, x0, x1, top, size))
    return [b["text"] for b in strip_page_furniture(blocks, H)]


def test_cabecalho_com_partes_na_mesma_altura():
    out = _page([("13816", 58, 75, 40, 9), ("Boletín Oficial de Canarias núm. 154, lunes 11 de agosto de 2003",
                                             346, 534, 40, 9)])
    assert "13816" not in out and not any("Boletín" in t for t in out)


def test_rodape_de_revista_e_paginacao_sem_page():
    out = _page([("Cell Chemical Biology 24, 1–9, November 16, 2017", 351, 543, 770, 8),
                 ("5 of 15", 536, 559, 40, 8)])
    assert not any("Cell Chemical" in t for t in out) and "5 of 15" not in out


def test_legenda_de_tabela_no_topo_fica():
    out = _page([("TABLE 1 Summary of features for selected chaperones", 50, 301, 40, 7)])
    assert any(t.startswith("TABLE 1") for t in out)


def test_poucas_linhas_tambem_limpa():
    blocks = [_line("Degree Programs", 476, 550, 10, 10), _line("Associate Degree Programs (2 years)", 37, 308, 60, 18),
              _line("Beijing Language And Culture University", 339, 518, 815, 10)]
    out = [b["text"] for b in strip_page_furniture(blocks, 842)]
    assert "Associate Degree Programs (2 years)" in out
    assert "Beijing Language And Culture University" not in out


def test_pdf_com_tres_colunas(tmp_path):
    pytest.importorskip("reportlab")
    from reportlab.pdfgen.canvas import Canvas

    from markinho.core import convert

    target = tmp_path / "jornal.pdf"
    c = Canvas(str(target), pagesize=(612, 792))
    c.setFont("Helvetica", 8)
    for col, x0 in enumerate((40, 222, 404)):
        for r in range(30):
            c.drawString(x0, 700 - r * 11, f"coluna{col} linha{r:02d} palavra mais texto aqui")
    c.save()
    md = convert(Path(target), "native").markdown
    pos = [md.find(f"coluna{k} linha00") for k in range(3)]
    assert all(p >= 0 for p in pos) and pos == sorted(pos)
    assert md.find("coluna0 linha29") < md.find("coluna1 linha00")   # coluna inteira antes da próxima
