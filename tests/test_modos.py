"""Modos Simples e Completo (como a calculadora do Windows)."""
import os
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
QtWidgets = pytest.importorskip("PySide6.QtWidgets")

ROOT = Path(__file__).resolve().parent.parent
FILES = [str(ROOT / "exemplos" / "relatorio.docx"), str(ROOT / "exemplos" / "clientes.csv")]


@pytest.fixture
def win(tmp_path, monkeypatch):
    from PySide6.QtCore import QSettings

    from markinho.gui import MainWindow

    QSettings.setPath(QSettings.IniFormat, QSettings.UserScope, str(tmp_path))
    QSettings.setDefaultFormat(QSettings.IniFormat)
    monkeypatch.setattr(MainWindow, "DEFAULT_MODE", "simple")       # como na 1ª abertura de verdade
    app = QtWidgets.QApplication.instance()
    QSettings("Markinho", "Markinho").remove("ui/mode")
    w = MainWindow()
    yield app, w
    w.close()


def wait(app, w, timeout=30):
    import time

    end = time.time() + timeout
    while any(e.busy for e in w.entries.values()) and time.time() < end:
        app.processEvents()
        time.sleep(0.02)
    app.processEvents()


def test_abre_no_simples_e_troca(win):
    app, w = win
    assert w.mode == "simple" and w.root_stack.currentWidget() is w.simple
    assert w.menuBar().isHidden() and w._toolbar.isHidden() and not w._dock.isVisible()
    assert w.simple.stack.currentIndex() == 0                    # área de soltar arquivos
    assert w.header.simple_btn.isChecked() and not w.header.help_btn.isHidden()
    w.set_mode("complete")
    assert w.root_stack.currentWidget() is w._main_split and not w.menuBar().isHidden()
    assert w.header.full_btn.isChecked() and w.header.help_btn.isHidden()
    assert w.list.parent() is w._left                            # a lista voltou para o Completo
    assert w.settings.value("ui/mode") == "complete"             # lembra o último modo
    w.set_mode("simple")
    assert w.list.parent() is not w._left


def test_simples_converte_sozinho_e_mostra_acoes(win):
    app, w = win
    w.add_paths(FILES)
    wait(app, w)
    assert all(e.result is not None for e in w.entries.values())   # sem precisar clicar em Converter
    w.list.setCurrentRow(0)
    app.processEvents()
    s = w.simple
    assert s.stack.currentIndex() == 1 and "(2)" in s.count.text()
    assert s.save_btn.isEnabled() and s.export_btn.isEnabled() and "palavras" in s.words.text()
    assert "Relat" in s.preview.toPlainText()
    w.set_mode("complete")                                        # mesma fila e mesmos textos
    assert len(w.entries) == 2 and w.list.count() == 2


def test_aviso_leva_ao_completo(win):
    app, w = win
    w.add_paths(FILES[:1])
    wait(app, w)
    w.list.setCurrentRow(0)
    e = w._current()
    e.result.warnings.append("OCR com baixa confiança na página 1")
    w.simple.refresh()
    assert not w.simple.warn.isHidden() and "modo completo" in w.simple.warn.text()
    w.open_in_complete()
    assert w.mode == "complete"


def test_anonimizar_e_a_mesma_opcao_do_painel(win, monkeypatch):
    from PySide6.QtWidgets import QDialog

    from markinho import gui

    app, w = win
    monkeypatch.setattr(gui.QDialog, "exec", lambda self: QDialog.Accepted)   # aviso da anonimização aceito
    w.simple.anon.setChecked(True)
    assert w.panel.anon.isChecked() == w.simple.anon.isChecked()


def test_exportar_rapido(win, tmp_path, monkeypatch):
    from PySide6.QtWidgets import QFileDialog, QMessageBox

    app, w = win
    w.add_paths(FILES[:1])
    wait(app, w)
    w.list.setCurrentRow(0)
    target = tmp_path / "saida.html"
    monkeypatch.setattr(QFileDialog, "getSaveFileName", staticmethod(lambda *a, **k: (str(target), "")))
    monkeypatch.setattr(QMessageBox, "exec", lambda self: 0)
    w.quick_export("html")
    assert target.is_file() and "Relat" in target.read_text(encoding="utf-8")
    assert not list(tmp_path.glob(".~*"))
    labels = [a.text() for a in w.simple.export_btn.menu().actions() if a.text()]
    assert any("Word" in t for t in labels) and any("Mais formatos" in t for t in labels)


def test_atalhos_de_modo(win):
    app, w = win
    keys = {a.shortcut().toString(): a for a in w.actions() if a.shortcut().toString() in ("Ctrl+1", "Ctrl+2")}
    keys["Ctrl+2"].trigger()
    assert w.mode == "complete"
    keys["Ctrl+1"].trigger()
    assert w.mode == "simple"
