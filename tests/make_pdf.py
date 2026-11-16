"""Gera um PDF de teste com títulos, parágrafos, lista, tabela e cabeçalho repetido."""
from pathlib import Path


def make_pdf(target: Path, pages: int = 3) -> Path:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table

    styles = getSampleStyleSheet()

    def header(canvas, doc):
        canvas.setFont("Helvetica", 8)
        canvas.drawString(72, A4[1] - 40, "Empresa Exemplo - Documento Interno")
        canvas.drawString(72, 30, f"Página {doc.page}")

    story = [Paragraph("Relatório Anual de Vendas", styles["Title"])]
    for p in range(pages):
        story += [Paragraph(f"Seção {p + 1}: Resultados", styles["Heading1"]),
                  Paragraph("As vendas cresceram de forma consistente ao longo do período analisado, "
                            "com destaque para a região Nordeste e para os produtos de maior valor "
                            "agregado. A equipe comercial superou as metas estabelecidas.", styles["Normal"]),
                  Spacer(1, 12),
                  Paragraph("Detalhes", styles["Heading2"]),
                  Paragraph("Segundo parágrafo com informação complementar sobre a seção.", styles["Normal"])]
        if p == 0:
            story += [Spacer(1, 12), Table([["Região", "Receita", "Meta"], ["Norte", "100", "90"],
                                            ["Nordeste", "250", "200"]],
                                           style=[("GRID", (0, 0), (-1, -1), 0.5, "black")])]
        story.append(PageBreak())
    SimpleDocTemplate(str(target), pagesize=A4, title="Relatório").build(
        story, onFirstPage=header, onLaterPages=header)
    return target


if __name__ == "__main__":
    import sys
    make_pdf(Path(sys.argv[1]))


def make_png(target: Path, text: str = "Relatório de Ação", size=(900, 200)) -> Path:
    from PIL import Image, ImageDraw, ImageFont

    img = Image.new("RGB", size, "white")
    d = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype("DejaVuSans.ttf", 48)
    except OSError:
        font = ImageFont.load_default()
    d.text((30, 60), text, fill="black", font=font)
    img.save(target)
    return target


def make_columns_pdf(target: Path) -> Path:
    """Duas colunas, bloco de código em fonte monoespaçada e uma imagem."""
    import tempfile

    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.platypus import (BaseDocTemplate, Frame, Image, PageTemplate, Paragraph, Preformatted,
                                    Spacer)

    styles = getSampleStyleSheet()
    w, h = A4
    full = Frame(50, h - 130, w - 100, 80, id="title")
    col_w = (w - 100 - 30) / 2
    left = Frame(50, 60, col_w, h - 200, id="left")
    right = Frame(50 + col_w + 30, 60, col_w, h - 200, id="right")
    doc = BaseDocTemplate(str(target), pagesize=A4, title="Artigo em Colunas")
    doc.addPageTemplates([PageTemplate(id="cols", frames=[full, left, right])])
    png = make_png(Path(tempfile.mkdtemp()) / "fig.png", "Figura 1", (400, 200))
    code_style = ParagraphStyle("code", fontName="Courier", fontSize=9, leading=11)
    from reportlab.platypus import FrameBreak

    story = [Paragraph("Artigo em Colunas", styles["Title"]), FrameBreak(),
             Paragraph("Introdução", styles["Heading2"])]
    story += [Paragraph("Primeira coluna, parágrafo %d. " % i + "Texto de exemplo da coluna esquerda. " * 4,
                        styles["Normal"]) for i in range(1, 4)]
    story += [Spacer(1, 6), Preformatted("def soma(a, b):\n    return a + b", code_style), FrameBreak(),
              Paragraph("Resultados", styles["Heading2"])]
    story += [Paragraph("Segunda coluna, parágrafo %d. " % i + "Texto de exemplo da coluna direita. " * 4,
                        styles["Normal"]) for i in range(1, 3)]
    story += [Image(str(png), width=150, height=75)]
    doc.build(story)
    return target


def make_scanned_pdf(target: Path) -> Path:
    """PDF só com imagem (sem camada de texto), como um documento escaneado."""
    from PIL import Image, ImageDraw, ImageFont

    img = Image.new("RGB", (1240, 1754), "white")
    d = ImageDraw.Draw(img)
    try:
        big = ImageFont.truetype("DejaVuSans-Bold.ttf", 56)
        font = ImageFont.truetype("DejaVuSans.ttf", 32)
    except OSError:
        big = font = ImageFont.load_default()
    d.text((100, 150), "Certidão de Conclusão", fill="black", font=big)
    d.text((100, 300), "Certificamos que a aluna concluiu o curso de", fill="black", font=font)
    d.text((100, 350), "Educação Ambiental com aproveitamento.", fill="black", font=font)
    img.save(target, "PDF", resolution=150)
    return target


def make_pje_pdf(target: Path, pages: int = 3) -> Path:
    """PDF no estilo do PJe: texto do processo, faixa vertical de assinatura e rodapé com código."""
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.pdfgen import canvas

    font = "Helvetica"
    try:
        pdfmetrics.registerFont(TTFont("DejaVu", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"))
        font = "DejaVu"
    except Exception:  # noqa: BLE001
        pass
    c = canvas.Canvas(str(target), pagesize=A4)
    w, h = A4
    for n in range(1, pages + 1):
        c.setFont(font, 16)
        if n == 1:
            c.drawString(72, h - 100, "SENTENÇA")
        c.setFont(font, 11)
        for k in range(12):
            c.drawString(72, h - 140 - k * 18, f"Página {n}, parágrafo {k + 1}: a parte autora requer a procedência.")
        c.saveState()
        c.translate(w - 20, 120)
        c.rotate(90)
        c.setFont(font, 7)
        c.drawString(0, 0, "Assinado eletronicamente por: JOAO DA SILVA - 10/03/2026 14:22:01")
        c.restoreState()
        c.setFont(font, 7)
        c.drawString(72, 30, f"https://pje.tjxx.jus.br:443/pje/Processo/ConsultaDocumento/listView.seam  Num. 98765 - Pág. {n}")
        c.showPage()
    c.save()
    return target


def make_booklet_pdf(target: Path) -> Path:
    """Cartilha diagramada: capa com fontes enormes (uma vez só), índice em negrito com números de
    página e seções com título grande em várias páginas (como PDFs feitos no InDesign)."""
    from reportlab.lib.pagesizes import A5
    from reportlab.pdfgen import canvas

    c = canvas.Canvas(str(target), pagesize=A5)
    c.setTitle("cartilha_final 1.indd")
    w, h = A5
    c.setFont("Helvetica-Bold", 32)
    c.drawString(40, h - 120, "GUIA DO VOLUNTARIO")
    c.setFont("Helvetica-Bold", 26)
    c.drawString(40, h - 160, "Edicao 2026")
    c.showPage()
    c.setFont("Helvetica-Bold", 22)
    c.drawString(40, h - 60, "ÍNDICE")
    c.setFont("Helvetica-Bold", 10)
    for k, item in enumerate(["Apresentação", "Direitos", "Deveres"]):
        c.drawString(40, h - 100 - 18 * k, item)
        c.drawString(w - 60, h - 100 - 18 * k, str(3 + k))
    c.showPage()
    for title in ("APRESENTAÇÃO", "DIREITOS", "DEVERES"):
        c.setFont("Helvetica-Bold", 22)
        c.drawString(40, h - 60, title)
        c.setFont("Helvetica", 10)
        for k in range(8):
            c.drawString(40, h - 100 - 14 * k, f"Texto da seção {title.lower()}, linha {k + 1} do conteúdo.")
        c.showPage()
    c.save()
    return target
