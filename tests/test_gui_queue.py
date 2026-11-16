"""Fila da interface: arquivos acumulam e só convertem ao clicar em Converter."""
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

    QSettings.setPath(QSettings.IniFormat, QSettings.UserScope, str(tmp_path))
    QSettings.setDefaultFormat(QSettings.IniFormat)
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    from markinho.gui import MainWindow

    w = MainWindow()
    w.settings.clear()
    w.act_auto.setChecked(False)
    yield app, w
    w.close()


def wait(app, w, timeout=30):
    import time

    end = time.time() + timeout
    while any(e.busy for e in w.entries.values()) and time.time() < end:
        app.processEvents()
        time.sleep(0.02)
    app.processEvents()


def test_files_accumulate_then_convert(win):
    app, w = win
    w.add_paths(FILES)
    assert all(e.queued and not e.busy and e.result is None for e in w.entries.values())
    assert w.act_convert.isEnabled() and "na fila" in w.statusBar().currentMessage()
    w.add_paths(FILES)                                   # repetidos são ignorados
    assert len(w.entries) == 2
    w.convert_queue()
    wait(app, w)
    assert all(e.result is not None and not e.queued for e in w.entries.values())
    w.list.clearSelection()
    w._update_buttons()
    assert not w.act_convert.isEnabled()              # nada na fila e nada selecionado


def test_auto_convert(win):
    app, w = win
    w.act_auto.setChecked(True)
    w.add_paths(FILES[:1])
    wait(app, w)
    assert next(iter(w.entries.values())).result is not None


def test_cancel_returns_to_queue(win):
    app, w = win
    w.add_paths(FILES)
    w.pool.setMaxThreadCount(1)
    w.convert_queue()
    w.cancel_conversions()
    wait(app, w)
    for e in w.entries.values():
        assert not e.busy and (e.queued or e.result is not None)


def test_rename_and_order_drive_names(win):
    app, w = win
    w.add_paths(FILES)
    w.convert_queue()
    wait(app, w)
    item = w.list.takeItem(1)                            # clientes.csv vai para o topo
    w.list.insertItem(0, item)
    w.entries[FILES[0]].custom = "Relatório Final"
    from markinho.naming import NamingOptions, plan

    names = [p.name for p in plan(w._contexts(w._done_entries()), NamingOptions("{n}_{nome}"))]
    assert names == ["001_clientes.md", "002_Relatório Final.md"]


def test_converted_file_can_be_converted_again(win):
    app, w = win
    w.add_paths(FILES[:1])
    w.convert_queue()
    wait(app, w)
    e = next(iter(w.entries.values()))
    first = e.result
    assert first is not None
    w.list.setCurrentRow(0)
    w.list.item(0).setSelected(True)
    w._update_buttons()
    assert w.act_convert.isEnabled()                 # arquivo com ✔ selecionado: dá para converter de novo
    w.convert_queue()
    assert e.busy
    wait(app, w)
    assert e.result is not None and e.result is not first and not e.error
