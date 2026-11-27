"""Interface das melhorias: colar, Copiar para IA, revisão de páginas, modo simples, ABNT e janelas."""
import os
import sys
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
QtWidgets = pytest.importorskip("PySide6.QtWidgets")
sys.path.insert(0, str(Path(__file__).parent))

ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture
def win(tmp_path):
    from PySide6.QtCore import QSettings

    QSettings.setPath(QSettings.IniFormat, QSettings.UserScope, str(tmp_path))
    QSettings.setDefaultFormat(QSettings.IniFormat)
    app = QtWidgets.QApplication.instance()
    from markinho.gui import MainWindow

    w = MainWindow()
    w.settings.clear()
    w.act_auto.setChecked(False)
    yield app, w
    w.close()


def wait(app, w, timeout=60):
    import time

    end = time.time() + timeout
    while any(e.busy for e in w.entries.values()) and time.time() < end:
        app.processEvents()
        time.sleep(0.02)
    app.processEvents()


def test_paste_html_creates_document(win):
    from PySide6.QtCore import QMimeData
    from PySide6.QtGui import QGuiApplication

    app, w = win
    mime = QMimeData()
    mime.setHtml("<h1>Ata</h1><p>Texto <i>colado</i> do navegador.</p>")
    mime.setText("Ata\nTexto colado do navegador.")
    QGuiApplication.clipboard().setMimeData(mime)
    w.paste_as_markdown()
    e = w._current()
    assert e is not None and "# Ata" in e.text and "*colado*" in e.text
    assert w.list.currentItem().text().startswith("Colado 1")


def test_ai_dialog_splits_and_copies(win):
    from PySide6.QtGui import QGuiApplication

    from markinho.gui_tools import AiCopyDialog

    app, w = win
    md = "\n\n".join(f"# Cap {i}\n\n" + "palavra " * 3000 for i in range(5))
    d = AiCopyDialog(w, md, w.settings)
    d.limit.setCurrentIndex(d.limit.findData(8_000))
    assert len(d.parts) > 1 and d.parts_list.count() == len(d.parts)
    d._copy_selected()
    assert QGuiApplication.clipboard().text().startswith("[Parte 1 de")


def test_review_banner_for_scanned_pdf_without_ocr(win):
    from make_pdf import make_scanned_pdf

    app, w = win
    pdf = make_scanned_pdf(Path(w.settings.fileName()).parent / "scan.pdf")
    w.settings.setValue("engine", "native")
    w.settings.setValue("opt/native/ocr", "off")
    w.panel.engine.setCurrentIndex(w.panel.engine.findData("native"))
    w.add_paths([str(pdf)])
    w.convert_queue()
    wait(app, w)
    w.list.setCurrentRow(0)
    e = w._current()
    assert e.result is not None and e.result.review_pages == [1]
    assert not w.review.isHidden() and "page:1" in w.review.text()
    assert w.list.item(0).text().endswith("⚠")


def test_simple_mode_hides_advanced(win):
    app, w = win
    w.act_simple.setChecked(True)
    assert w.panel.engine_box.isHidden() and w.panel.fix_box.isHidden()
    w.act_simple.setChecked(False)
    assert not w.panel.engine_box.isHidden()


def test_export_dialog_abnt_option(win):
    from markinho.gui import ExportDialog

    app, w = win
    d = ExportDialog(w, w.settings, 1, 1)
    d.fmt.setCurrentIndex(d.fmt.findData("docx"))
    d.template.setCurrentIndex(d.template.findData("abnt"))
    assert not d.template.isHidden() and d.numbers.isChecked() and d.numbers.isEnabled()
    fid, _backend, opts, _scope = d.values()
    assert fid == "docx" and opts["template"] == "abnt" and opts["number_sections"]
    d.fmt.setCurrentIndex(d.fmt.findData("html"))
    assert d.template.isHidden()


def test_first_run_sets_purpose(win):
    from markinho.gui_tools import FirstRunDialog

    app, w = win
    d = FirstRunDialog(w, w.settings)
    d.group.button(0).setChecked(True)          # IA
    d._ok()
    assert w.settings.value("out/profile") == "llm" and w.settings.value("out/images") == "none"
    assert w.settings.value("ui/first_run_done", False, type=bool)


def test_split_and_error_report_dialogs(win, tmp_path, monkeypatch):
    from PySide6.QtWidgets import QMessageBox

    from markinho.gui_tools import ErrorReportDialog, SplitDialog

    app, w = win
    monkeypatch.setattr(QMessageBox, "information", staticmethod(lambda *a, **k: None))
    d = SplitDialog(w, "# Um\n\na\n\n# Dois\n\nb\n", {}, w.settings, str(tmp_path / "partes"))
    d._save()
    assert sorted(p.name for p in (tmp_path / "partes").iterdir()) == ["01_Um.md", "02_Dois.md"]
    r = ErrorReportDialog(w, w.settings)
    assert "Relatório de erro do Markinho" in r.text.toPlainText()


def test_right_click_popups(win, tmp_path):
    from markinho.gui_tools import DoneDialog, ExportChoiceDialog, ProgressPopup
    from markinho.quick import QuickResult

    app, w = win
    pop = ProgressPopup(w.settings)
    pop.start(4)
    pop.set_file("a.pdf", 1, 4)
    pop.set_progress(1, 4, 0.5)
    assert pop.bar.value() == 38                       # (1 + 0,5) / 4
    pop.show_next.setChecked(False)
    assert not w.settings.value("quick/show_progress", True, type=bool)
    pop.close()
    ch = ExportChoiceDialog(None, w.settings)
    ch.fmt.setCurrentIndex(ch.fmt.findData("docx"))
    ch.abnt.setChecked(True)
    assert ch.values() == ("docx", {"template": "abnt", "number_sections": True}, ".docx")
    out = tmp_path / "r.md"
    out.write_text("x")
    d = DoneDialog([QuickResult(tmp_path / "r.docx", out)])
    labels = [b.text() for b in d.findChildren(QtWidgets.QPushButton)]
    assert "Abrir arquivo" in labels and "Abrir pasta" in labels
    d2 = DoneDialog([QuickResult(tmp_path / "x.pdf", error="falhou")], stopped=True, skipped=2)
    assert "interrompida" in d2.windowTitle()


def test_engines_dialog_use_button(win):
    from markinho.gui import EnginesDialog

    app, w = win
    d = EnginesDialog(w)
    assert d.use_btns["auto"].text() == "✓ Em uso"
    d._use("native")
    assert w.panel.engine_id() == "native" and d.use_btns["native"].text() == "✓ Em uso"
    assert "marker" not in d.use_btns and "marker" not in d.btns       # não instalado: sem botões


def test_ollama_missing_shows_inline_help_without_freezing(win, monkeypatch):
    import time

    import markinho.describe as describe

    app, w = win
    monkeypatch.setattr(describe, "list_models", lambda *a, **k: [])
    w.panel.describe.setChecked(True)                  # procura sozinho, em segundo plano
    end = time.time() + 5
    while "não foi encontrado" not in w.panel.ollama_status.text() and time.time() < end:
        app.processEvents()
        time.sleep(0.02)
    # o aviso traz o link de download do Ollama (confere o endereço do link, não um pedaço do texto)
    import re
    from urllib.parse import urlparse

    links = re.findall(r"href=['\"]([^'\"]+)['\"]", w.panel.ollama_status.text())
    assert any(urlparse(u).hostname == "ollama.com" for u in links) and w.panel.ollama_model.isEnabled()
    monkeypatch.setattr(describe, "list_models", lambda *a, **k: ["qwen2.5vl:3b", "llama3"])
    w.panel._refresh_ollama()
    end = time.time() + 5
    while "✓" not in w.panel.ollama_status.text() and time.time() < end:
        app.processEvents()
        time.sleep(0.02)
    assert w.panel.ollama_model.itemText(0) == "qwen2.5vl:3b"
    w.panel.describe.setChecked(False)
    assert not w.panel.ollama_model.isEnabled()


def test_settings_change_offers_reconvert_and_conflict_alert(win):
    from test_gui_queue import FILES

    app, w = win
    w.add_paths(FILES[:1])
    w.convert_queue()
    wait(app, w)
    w.list.setCurrentRow(0)
    first = w._current().result
    target = "rapido" if w.panel.mode.currentData() != "rapido" else "equilibrado"
    w.panel.mode.setCurrentIndex(w.panel.mode.findData(target))     # mudou o modo
    assert not w.settings_bar.isHidden() and "mudaram" in w.settings_bar_label.text()
    w._redo_current()
    assert w.settings_bar.isHidden() and w._current().busy
    wait(app, w)
    assert w._current().result is not first
    # alerta: descrever imagens com perfil que remove imagens
    w.panel.profile.setCurrentIndex(w.panel.profile.findData("llm"))
    w.panel.describe.setChecked(True)
    assert not w.panel.conflict_box.isHidden() and "não vai aparecer" in w.panel.conflict_label.text()
    w.panel.images.setCurrentIndex(w.panel.images.findData("none"))
    w.panel.conflict_fix.click()                       # 1º conflito: perfil
    assert w.panel.profile.currentData() == "gfm"
    assert not w.panel.conflict_box.isHidden() and "não incluir" in w.panel.conflict_label.text()
    w.panel.conflict_fix.click()                       # 2º conflito: imagens desligadas
    assert w.panel.images.currentData() == "folder" and w.panel.conflict_box.isHidden()


def test_original_follows_reading(win, tmp_path):
    from make_pdf import make_pdf

    app, w = win
    pdf = make_pdf(tmp_path / "longo.pdf", pages=12)
    w.add_paths([str(pdf)])
    w.convert_queue()
    wait(app, w)
    w.list.setCurrentRow(0)
    e = w._current()
    assert len(e.result.page_starts) == 12
    w.resize(1200, 500)
    w.show()
    w.compare_btn.setChecked(True)
    assert w.compare_btn.text() == "Ver original ao lado" and not w.space_btn.isHidden()
    for _ in range(20):
        app.processEvents()
    if not w.original.is_pdf():
        pytest.skip("QtPdf indisponível")
    from markinho.pagesync import page_positions, position_of

    w.tabs.setCurrentIndex(0)
    pos = position_of(page_positions(e.result.page_starts, w.editor.toPlainText()), 6)
    from markinho.gui import scroll_text_to

    scroll_text_to(w.editor, pos)
    w._sync_to_original()
    assert w.original.current_page() == 6
    w.space_btn.setChecked(True)
    assert w._left.isHidden() and w._dock.isHidden()
    w.compare_btn.setChecked(False)
    assert not w._left.isHidden() and not w.space_btn.isChecked()


def test_zoom_text_and_pdf(win, tmp_path):
    from make_pdf import make_pdf

    app, w = win
    base = w.editor.font().pointSizeF()
    w.text_zoom(1)
    w.text_zoom(1)
    assert w.editor.font().pointSizeF() > base and int(w.settings.value("ui/text_zoom")) == 2
    w.text_zoom(0)
    assert abs(w.editor.font().pointSizeF() - base) < 0.01
    w.resize(1200, 600)
    w.show()
    w.original.setVisible(True)
    w.original.load(make_pdf(tmp_path / "z.pdf", pages=6))
    app.processEvents()
    if not w.original.is_pdf():
        pytest.skip("QtPdf indisponível")
    assert w.original.zoom_label.text() == "Largura"
    w.original.zoom(1.2)
    z1 = w.original.pdf_view.zoomFactor()
    w.original.zoom(1.2)
    assert w.original.pdf_view.zoomFactor() > z1 and w.original.zoom_label.text().endswith("%")
    w.original.fit_width()
    assert w.original.zoom_label.text() == "Largura"
    import time

    def pump():
        end = time.time() + 0.5
        while time.time() < end:
            app.processEvents()
            time.sleep(0.02)

    w.original.go_to_page(4)
    pump()
    before = w.original.current_page()
    w.original.zoom(1.4)
    pump()
    assert w.original.current_page() == before         # o zoom não muda a página que se está lendo


def test_follow_toggle_aligns_on_enable(win, tmp_path):
    from make_pdf import make_pdf

    from markinho.gui import scroll_text_to
    from markinho.pagesync import page_positions, position_of

    app, w = win
    w.add_paths([str(make_pdf(tmp_path / "p.pdf", pages=12))])
    w.convert_queue()
    wait(app, w)
    w.list.setCurrentRow(0)
    w.resize(1200, 500)
    w.show()
    w.compare_btn.setChecked(True)
    for _ in range(20):
        app.processEvents()
    if not w.original.is_pdf():
        pytest.skip("QtPdf indisponível")
    w.tabs.setCurrentIndex(0)
    w.follow_cb.setChecked(False)                      # desligado: lados independentes
    e = w._current()
    scroll_text_to(w.editor, position_of(page_positions(e.result.page_starts, w.editor.toPlainText()), 7))
    w._sync_to_original()
    assert w.original.current_page() == 1
    w.follow_cb.setChecked(True)                       # ligar alinha na hora
    assert w.original.current_page() == 7


def test_dialogs_remember_last_folder(win, tmp_path):
    from markinho.gui import recall_dir, remember_dir

    app, w = win
    a, b = tmp_path / "entrada", tmp_path / "saida"
    a.mkdir()
    b.mkdir()
    remember_dir(w.settings, a / "doc.pdf", "open")
    assert recall_dir(w.settings, "open") == str(a)
    assert recall_dir(w.settings, "save") == str(a)        # sem pasta própria: a última usada em qualquer janela
    remember_dir(w.settings, b / "doc.md", "save")
    assert recall_dir(w.settings, "save") == str(b) and recall_dir(w.settings, "open") == str(a)
    import shutil

    shutil.rmtree(b)
    assert Path(recall_dir(w.settings, "save")).is_dir()    # pasta apagada: não abre num lugar que não existe


def test_anon_warning_is_visible_and_needs_ack(win, monkeypatch):
    from PySide6.QtWidgets import QMessageBox

    win = win[1]

    shown = []

    def fake_exec(box):
        shown.append(box.text())
        box._clicked = None
        return 0

    monkeypatch.setattr(QMessageBox, "exec", fake_exec)
    monkeypatch.setattr(QMessageBox, "clickedButton", lambda box: None)
    win.panel.settings.remove("anon/ack")
    win.panel.anon.setChecked(True)                 # sem confirmar: volta a desligar
    assert shown and "não se responsabiliza" in shown[0] and not win.panel.anon.isChecked()
    win.panel.settings.setValue("anon/ack", True)
    win.panel.anon.setChecked(True)
    assert win.panel.anon.isChecked() and not win.panel.anon_warn.isHidden()
    assert "responsabiliza" in win.panel.anon_warn.text()
    win.panel.anon.setChecked(False)
    assert win.panel.anon_warn.isHidden()


def test_anon_dialog_recounts_after_pause(win):
    from PySide6.QtCore import QSettings

    from markinho.gui_tools import AnonDialog

    app, w = win
    d = AnonDialog(w, QSettings(), "Fulano Beltrano e Fulano Beltrano", None)
    calls = []
    d._recount.timeout.connect(lambda: calls.append(1))
    for ch in "Fulano":
        d.words.insertPlainText(ch)                 # cada letra só reinicia o relógio
    assert not calls and d._recount.isActive()
    import time

    end = time.time() + 3
    while not calls and time.time() < end:
        app.processEvents()
        time.sleep(0.05)
    assert calls == [1] and "Sua lista" in d.found.text()


def test_ux_menus_panel_and_header(win):
    from markinho.gui import num_br

    app, w = win
    titles = [a.text() for a in w.menuBar().actions()]
    assert titles[:5] == ["Arquivo", "Editar", "Exibir", "Ferramentas", "Ajuda"]
    # opções avançadas abrem e fecham; o estado é lembrado
    w.panel.adv_toggle.setChecked(False)
    assert w.panel.advanced.isHidden()
    w.panel.adv_toggle.setChecked(True)
    assert not w.panel.advanced.isHidden() and w.settings.value("ui/advanced", type=bool)
    # correção de caracteres resumida
    assert w.panel.fix_details.isHidden() and "correções ligadas" in w.panel.fix_summary.text()
    # números no formato brasileiro
    assert num_br(1023) == "1.023" and num_br(1234567) == "1.234.567"
    # janela estreita: botões secundários só com ícone
    from PySide6.QtCore import Qt

    w.show()
    w.resize(1000, 700)
    app.processEvents()
    assert w._toolbar.widgetForAction(w.act_copy).toolButtonStyle() == Qt.ToolButtonIconOnly
    w.resize(1400, 800)
    app.processEvents()
    assert w._toolbar.widgetForAction(w.act_copy).toolButtonStyle() == Qt.ToolButtonTextBesideIcon
    w.panel.adv_toggle.setChecked(False)


def test_support_milestones_and_dialog(tmp_path):
    from PySide6.QtCore import QSettings

    from markinho.gui_tools import SupportDialog
    from markinho.support import PIX_KEY, PIX_PAYLOAD, count_conversion, pix_crc_ok

    assert pix_crc_ok() and PIX_KEY in PIX_PAYLOAD and "MARKINHO" in PIX_PAYLOAD
    s = QSettings(str(tmp_path / "s.ini"), QSettings.IniFormat)
    hits = [m for _ in range(1000) if (m := count_conversion(s))]
    assert hits == [100, 1000]                       # uma vez em cada marco
    assert count_conversion(s) is None and int(s.value("stats/converted")) == 1001
    s2 = QSettings(str(tmp_path / "s2.ini"), QSettings.IniFormat)
    s2.setValue("support/never", True)
    assert not any(count_conversion(s2) for _ in range(150))   # “não mostrar de novo” vale para sempre
    d = SupportDialog(None, 100, s2)
    assert "100 documentos" in d.findChildren(type(d.layout().itemAt(0).widget()))[0].text()
