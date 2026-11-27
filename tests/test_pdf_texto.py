"""PDF nativo: espaço estreito entre palavras (LaTeX, jornais) e seções numeradas em negrito."""
from pathlib import Path

import pytest

pytest.importorskip("reportlab")

from markinho.core import convert


def _tight_words(target: Path) -> Path:
    """Palavras desenhadas uma a uma, separadas por 1,5 pt e sem o caractere de espaço (como faz o LaTeX)."""
    from reportlab.pdfbase.pdfmetrics import stringWidth
    from reportlab.pdfgen.canvas import Canvas

    c = Canvas(str(target))
    y = 760
    for line in ("Despite the substantial improvements achieved with machine learning approaches",
                 "document conversion remains a challenging problem for many documents"):
        x = 72
        for w in line.split():
            c.setFont("Times-Roman", 10)
            c.drawString(x, y, w)
            x += stringWidth(w, "Times-Roman", 10) + 1.5
        y -= 14
    c.save()
    return target


def test_palavras_com_espaco_estreito_nao_grudam(tmp_path):
    md = convert(_tight_words(tmp_path / "apertado.pdf"), "native").markdown
    assert "Despite the substantial improvements" in md
    assert "Despitethe" not in md


def _sections(target: Path) -> Path:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

    body = ParagraphStyle("b", fontName="Helvetica", fontSize=10, leading=13)
    bold = ParagraphStyle("h", fontName="Helvetica-Bold", fontSize=10, leading=13)
    title = ParagraphStyle("t", fontName="Helvetica-Bold", fontSize=18, leading=22)
    text = ("Este é um parágrafo comum do artigo, com várias palavras para formar uma linha inteira de texto "
            "e mais algumas para quebrar a linha e continuar logo abaixo, como acontece no corpo.")
    story = [Paragraph("Título do Artigo", title), Spacer(1, 12)]
    for head in ("1. Introdução", "2. Métodos", "2.1. Coleta de dados", "3. Resultados"):
        story += [Paragraph(head, bold), Spacer(1, 4), Paragraph(text, body), Spacer(1, 10)]
    story += [Paragraph("1. Este item numerado em negrito é uma frase longa que termina com ponto final.", bold),
              Paragraph(text, body)]
    SimpleDocTemplate(str(target), pagesize=A4).build(story)
    return target


def test_secoes_numeradas_em_negrito_viram_titulos(tmp_path):
    md = convert(_sections(tmp_path / "artigo.pdf"), "native").markdown
    heads = [ln for ln in md.splitlines() if ln.startswith("#")]
    assert any(h.endswith("1. Introdução") for h in heads)
    assert any(h.endswith("3. Resultados") for h in heads)
    sub = next(h for h in heads if h.endswith("2.1. Coleta de dados"))
    main = next(h for h in heads if h.endswith("2. Métodos"))
    assert len(sub.split()[0]) == len(main.split()[0]) + 1          # subseção um nível abaixo
    assert not any("termina com ponto final" in h for h in heads)    # frase numerada não é título
