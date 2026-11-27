"""Tabela longa que quebra entre páginas vira uma tabela só (pedido de usuários: estragava os pedaços de RAG)."""
from pathlib import Path

import pytest

pytest.importorskip("reportlab")

from markinho.core import convert
from markinho.pdf import merge_split_tables


def _long_table(target: Path, rows: int = 90, repeat_header: bool = True) -> Path:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Table

    st = getSampleStyleSheet()
    data = [["Código", "Produto", "Quantidade"]] + [[f"{i:03d}", f"Item {i}", str(i * 3)] for i in range(1, rows + 1)]
    table = Table(data, repeatRows=1 if repeat_header else 0, style=[("GRID", (0, 0), (-1, -1), 0.5, "black")])
    story = [Paragraph("Relatório de estoque", st["Title"]), table, Paragraph("Fim do relatório.", st["Normal"])]
    SimpleDocTemplate(str(target), pagesize=A4).build(story)
    return target


def _tables(md: str) -> list[list[str]]:
    out, cur = [], []
    for ln in md.splitlines():
        if ln.startswith("|"):
            cur.append(ln)
        elif cur:
            out.append(cur)
            cur = []
    return out + ([cur] if cur else [])


@pytest.mark.parametrize("repeat_header", [True, False])
def test_tabela_de_varias_paginas_fica_inteira(tmp_path, repeat_header):
    pdf = _long_table(tmp_path / "estoque.pdf", rows=120, repeat_header=repeat_header)
    res = convert(pdf, "native")
    tables = _tables(res.markdown)
    assert len(tables) == 1, [t[:2] for t in tables]
    body = "\n".join(tables[0])
    assert "| 001 " in body and "| 120 " in body
    assert body.count("Código") == 1                       # cabeçalho repetido nas páginas novas saiu
    assert "Fim do relatório." in res.markdown


def test_opcao_desligada_mantem_tabelas_separadas(tmp_path):
    pdf = _long_table(tmp_path / "estoque.pdf", rows=120)
    md = convert(pdf, "native", {"pdf_merge_tables": False}).markdown
    assert len(_tables(md)) >= 2


def _t(rows, top=100.0):
    return {"kind": "table", "rows": rows, "text": "", "top": top}


def _ln(text, margin=False):
    return {"kind": "line", "text": text, "margin": margin}


def test_regras_da_juncao():
    head = ["A", "B"]
    pages = [(0, [_ln("Texto"), _t([head, ["1", "2"]]), _ln("Página 1 de 3", margin=True)]),
             (1, [_ln("(continua)"), _t([head, ["3", "4"]]), _ln("Depois da tabela")]),
             (2, [_t([["x", "y", "z"], ["5", "6", "7"]])])]          # outra tabela (3 colunas): não junta
    out, n = merge_split_tables(pages)
    assert n == 1
    assert out[0][1][1]["rows"] == [head, ["1", "2"], ["3", "4"]]
    assert [b["text"] for b in out[1][1]] == ["Depois da tabela"]
    assert len(out[2][1]) == 1
    # texto comum entre as tabelas: não junta
    pages = [(0, [_t([head, ["1", "2"]]), _ln("Um parágrafo de verdade no fim da página.")]),
             (1, [_t([head, ["3", "4"]])])]
    assert merge_split_tables(pages)[1] == 0
    # páginas não seguidas (intervalo escolhido pelo usuário): não junta
    assert merge_split_tables([(0, [_t([head, ["1", "2"]])]), (5, [_t([head, ["3", "4"]])])])[1] == 0
    # três páginas: a do meio é só continuação
    pages = [(0, [_t([head, ["1", "2"]])]), (1, [_t([["3", "4"]])]), (2, [_t([["5", "6"]]), _ln("fim")])]
    out, n = merge_split_tables(pages)
    assert n == 2 and out[0][1][0]["rows"][-1] == ["5", "6"]


def _sem_linhas(target: Path) -> Path:
    """Tabela sem nenhuma linha desenhada (só alinhamento), entre parágrafos comuns."""
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table

    st = getSampleStyleSheet()
    data = [["Região", "Receita", "Meta"], ["Norte", "1.234,56", "1.100"], ["Nordeste", "2.508,10", "2.000"],
            ["Sudeste", "4.870,00", "5.000"], ["Sul", "3.001,00", "2.900"]]
    texto = ("Este é um parágrafo comum com várias palavras para formar linhas inteiras de texto corrido, "
             "que não devem virar tabela de jeito nenhum, mesmo quando a página tem uma tabela logo abaixo.")
    story = [Paragraph("Vendas", st["Title"]), Paragraph(texto, st["Normal"]), Spacer(1, 12),
             Table(data, colWidths=[120, 90, 90]), Spacer(1, 12), Paragraph(texto, st["Normal"])]
    SimpleDocTemplate(str(target), pagesize=A4).build(story)
    return target


def test_tabela_sem_linhas_desenhadas(tmp_path):
    md = convert(_sem_linhas(tmp_path / "sem_linhas.pdf"), "native").markdown
    tables = _tables(md)
    assert len(tables) == 1
    body = "\n".join(tables[0])
    assert "| Região | Receita | Meta |" in body and "| Nordeste | 2.508,10 | 2.000 |" in body
    assert "parágrafo comum" not in body                          # o texto corrido ficou fora da tabela


def test_colunas_de_texto_nao_viram_tabela(tmp_path):
    from reportlab.pdfgen.canvas import Canvas

    target = tmp_path / "jornal.pdf"
    c = Canvas(str(target))
    frase = "palavras de uma notícia comprida que continua"
    for col in range(4):                                          # 4 colunas estreitas de texto corrido
        y = 780
        for i in range(25):
            c.setFont("Times-Roman", 8)
            c.drawString(40 + col * 135, y, f"{frase} {i}")
            y -= 10
    c.save()
    assert not _tables(convert(target, "native").markdown)


def _numeros(target: Path) -> Path:
    from reportlab.pdfbase.pdfmetrics import stringWidth
    from reportlab.pdfgen.canvas import Canvas

    c = Canvas(str(target))
    data = [["Transição", "Média", "Erro", "Fonte"], ["DFS to DFS", "0.763", "0.030", "[18]"],
            ["DFS to DM", "0.196", "0.030", "[18]"], ["DM to Death", "0.152", "0.021", "[17]"],
            ["Recidiva", "0.081", "0.011", "[19]"]]
    widths = [max(stringWidth(r[k], "Helvetica", 9) for r in data) for k in range(4)]
    y = 700
    for row in data:
        x = 72
        for k, cell in enumerate(row):
            c.setFont("Helvetica", 9)
            c.drawString(x, y, cell)
            x += widths[k] + (30 if k == 0 else 4)                # números a só 4 pt uns dos outros
        y -= 13
    c.save()
    return target


def test_colunas_de_numeros_bem_juntas(tmp_path):
    """Colunas de números a meio espaço de distância não grudam numa célula só (“0.763 0.030”)."""
    tables = _tables(convert(_numeros(tmp_path / "numeros.pdf"), "native").markdown)
    assert tables
    body = "\n".join(tables[0])
    assert "| DFS to DFS | 0.763 | 0.030 | [18] |" in body


def test_rodape_de_revista_e_numero_de_pagina_saem(tmp_path):
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen.canvas import Canvas

    target = tmp_path / "artigo.pdf"
    c = Canvas(str(target), pagesize=A4)
    W, H = A4
    c.setFont("Helvetica", 7)
    c.drawString(72, H - 30, "Revista Brasileira de Testes Vol. 12, No. 3 (2024) 45-67")
    c.setFont("Helvetica-Bold", 16)
    c.drawString(72, H - 90, "Título do Artigo Científico")
    c.setFont("Helvetica", 10)
    y = H - 130
    for i in range(30):
        c.drawString(72, y, f"Linha {i} do corpo do artigo com bastante texto corrido para ocupar a página.")
        y -= 14
    c.setFont("Helvetica", 7)
    c.drawString(72, 40, "Please cite this article as: Silva et al. https://doi.org/10.1000/teste")
    c.setFont("Helvetica", 9)
    c.drawString(W / 2, 25, "45")
    c.save()
    md = convert(target, "native").markdown
    assert "Título do Artigo Científico" in md and "Linha 29 do corpo" in md
    assert "Revista Brasileira" not in md and "Please cite" not in md
    assert "\n45\n" not in f"\n{md}\n"
