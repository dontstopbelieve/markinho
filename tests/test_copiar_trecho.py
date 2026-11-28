# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 dontstopbelieve — Markinho
"""Copiar e Copiar para IA: com um trecho selecionado, só o trecho; sem seleção, o documento todo."""
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture
def win(tmp_path):
    from PySide6.QtCore import QSettings

    QSettings.setPath(QSettings.IniFormat, QSettings.UserScope, str(tmp_path))
    QSettings.setDefaultFormat(QSettings.IniFormat)
    from markinho.gui import MainWindow

    w = MainWindow()
    w.settings.clear()
    w.show()
    yield w
    w.close()


def _select(editor, start, end):
    from PySide6.QtGui import QTextCursor

    c = editor.textCursor()
    c.setPosition(start)
    c.setPosition(end, QTextCursor.KeepAnchor)
    editor.setTextCursor(c)


def test_copiar_so_o_trecho(win):
    from PySide6.QtGui import QGuiApplication

    win.editor.setPlainText("# Título\n\nPrimeiro parágrafo.\n\nSegundo parágrafo.")
    win.copy_current()
    assert QGuiApplication.clipboard().text().startswith("# Título")
    _select(win.editor, 10, 29)
    win.copy_current()
    assert QGuiApplication.clipboard().text() == "Primeiro parágrafo."


def test_para_ia_so_o_trecho(win, monkeypatch):
    import markinho.gui_tools as gt

    got = {}

    class Fake:
        def __init__(self, parent, text, settings, selection=False):
            got.update(text=text, selection=selection)

        def exec(self):
            return 0

    monkeypatch.setattr(gt, "AiCopyDialog", Fake)

    class E:
        text = "# Título\n\nPrimeiro parágrafo.\n\nSegundo parágrafo."
        result = object()
        edited = True

    monkeypatch.setattr(win, "_current", lambda: E())
    win.editor.setPlainText(E.text)
    _select(win.editor, 10, 29)
    win.copy_for_ai()
    assert got == {"text": "Primeiro parágrafo.", "selection": True}
    win.editor.moveCursor(win.editor.textCursor().MoveOperation.End)
    win.copy_for_ai()
    assert got["text"] == E.text and got["selection"] is False


def test_janela_avisa_que_e_so_o_trecho(tmp_path):
    from PySide6.QtCore import QSettings
    from PySide6.QtWidgets import QLabel

    from markinho.gui_tools import AiCopyDialog

    s = QSettings(str(tmp_path / "m.ini"), QSettings.IniFormat)
    d = AiCopyDialog(None, "Um trecho.", s, selection=True)
    assert any("Só o trecho" in lb.text() for lb in d.findChildren(QLabel))
