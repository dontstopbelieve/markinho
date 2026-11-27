"""Novidades de 27/11/2026: sumário, comparação de versões, prévia, imagem como tabela/código, código colorido."""
import shutil
import time
from pathlib import Path

import pytest

EX = Path(__file__).resolve().parent.parent / "exemplos"


def test_outline_ignores_code_and_frontmatter():
    from markinho.outline import headings

    md = '---\ntitle: "x"\n---\n# Título\n\n```\n# não é título\n```\n## Seção **um**\ntexto\n### Sub'
    assert headings(md) == [(1, "Título", 3), (2, "Seção um", 8), (3, "Sub", 10)]


def test_compare_versions():
    from markinho.compare import compare, to_html, word_diff_html

    a = "# Contrato\n\nO prazo é de 30 dias.\n\nMulta de 10%.\n\nO foro é o de Campinas.\n\n<!-- página 2 -->"
    b = "# Contrato\n\nO prazo é de 45 dias.\n\nMulta de 10%.\n\nAs partes podem rescindir.\n\nAnexo novo."
    c = compare(a, b)
    kinds = [x.kind for x in c.changes if x.kind != "igual"]
    assert kinds.count("alterado") == 1 and "removido" in kinds and kinds.count("novo") >= 1
    assert "<del>30</del>" in word_diff_html("O prazo é de 30 dias.", "O prazo é de 45 dias.")
    page = to_html(c, "v1.pdf", "v2.pdf")
    assert "ALTERADO" in page and "v2.pdf" in page and "página 2" not in page
    assert compare("a\n\nb", "a\n\nb").summary().startswith("As duas versões têm o mesmo texto")


def test_partial_text_while_converting():
    from markinho.core import convert

    got = []
    r = convert(EX / "relatorio.pdf", "native", partial=lambda p, t: got.append((p, t)))
    assert [p for p, _ in got] == [1, 2, 3] and all(t for _, t in got) and r.markdown


def test_code_highlight_in_html():
    from markinho.exporter import markdown_to_html

    html = markdown_to_html("```python\ndef f():\n    return 1\n```", highlight=True)
    assert "<span style=" in html and "def" in html
    assert "<span style=" not in markdown_to_html("```python\ndef f(): pass\n```")


def _make_images(tmp_path):
    from PIL import Image, ImageDraw, ImageFont

    fonts = sorted(Path("/usr/share/fonts").rglob("DejaVuSans*.ttf")) if Path("/usr/share/fonts").is_dir() else []
    if not fonts:
        pytest.skip("sem fontes para desenhar a imagem de teste")
    mono = next((f for f in fonts if "Mono" in f.name), fonts[0])
    sans = next((f for f in fonts if f.name == "DejaVuSans.ttf"), fonts[0])
    f, m = ImageFont.truetype(str(sans), 36), ImageFont.truetype(str(mono), 34)
    tab = Image.new("RGB", (1400, 420), "white")
    d = ImageDraw.Draw(tab)
    for r, row in enumerate([("Região", "Receita", "Meta"), ("Norte", "100", "90"), ("Sul", "310", "300")]):
        for c, t in enumerate(row):
            d.text((60 + c * 450, 40 + r * 90), t, fill="black", font=f)
    tab.save(tmp_path / "tabela.png")
    code = Image.new("RGB", (1200, 300), "white")
    d = ImageDraw.Draw(code)
    for i, line in enumerate(["def soma(a, b):", "    return a + b", "", "print(soma(1, 2))"]):
        d.text((40, 30 + i * 60), line, fill="black", font=m)
    code.save(tmp_path / "codigo.png")


def test_read_image_as_table_and_code(tmp_path):
    from markinho import ocr

    if "tesseract" not in ocr.available_backends():
        pytest.skip("Tesseract não instalado")
    from markinho.core import convert

    _make_images(tmp_path)
    t = convert(tmp_path / "tabela.png", "native", {"image_mode": "table", "image_embed_original": False}).markdown
    assert "| Região | Receita | Meta |" in t and "| Sul | 310 | 300 |" in t
    c = convert(tmp_path / "codigo.png", "native", {"image_mode": "code", "image_embed_original": False}).markdown
    assert "```" in c and "\n    return a + b" in c


def test_words_to_table_groups_rows_and_columns():
    from markinho.ocr import words_to_table

    words = [{"text": t, "x0": x, "x1": x + 40, "top": y, "bottom": y + 20}
             for y, row in ((0, ((0, "A"), (300, "B"))), (40, ((0, "c1"), (300, "c2"))))
             for x, t in row]
    assert words_to_table(words) == [["A", "B"], ["c1", "c2"]]


def test_welcome_steps_outline_and_compare_dialog(tmp_path):
    from PySide6.QtCore import QSettings
    from PySide6.QtWidgets import QApplication

    QSettings.setPath(QSettings.IniFormat, QSettings.UserScope, str(tmp_path))
    QSettings.setDefaultFormat(QSettings.IniFormat)
    app = QApplication.instance()
    from markinho.gui import MainWindow
    from markinho.gui_tools import CompareDialog

    w = MainWindow()
    w.act_auto.setChecked(False)
    assert w.center_stack.currentIndex() == 0 and "Adicionar" in w.steps.text()      # boas-vindas
    md = tmp_path / "manual.md"
    md.write_text("# Manual\n\n## Instalação\n\nTexto.\n\n## Uso\n\nFim.\n", encoding="utf-8")
    w.add_paths([str(md)])
    app.processEvents()
    assert w.center_stack.currentIndex() == 1
    w.convert_queue()
    end = time.time() + 30
    while any(e.busy for e in w.entries.values()) and time.time() < end:
        app.processEvents()
        time.sleep(0.05)
    w.list.setCurrentRow(0)
    w.act_outline.setChecked(True)
    w._refresh_outline()
    assert w.outline.count() == 3 and not w.outline_box.isHidden()
    w._go_heading(w.outline.item(2))
    assert w.editor.textCursor().blockNumber() == 6
    assert "Salvar" in w.steps.text()
    v1, v2 = tmp_path / "v1.md", tmp_path / "v2.md"
    v1.write_text("# A\n\nprazo de 30 dias\n", encoding="utf-8")
    v2.write_text("# A\n\nprazo de 45 dias\n", encoding="utf-8")
    d = CompareDialog(w, w.settings)
    d.path_a.setText(str(v1))
    d.path_b.setText(str(v2))
    d.run()
    assert "alterado" in d.summary.text() and d.b_save.isEnabled()
    w.close()
