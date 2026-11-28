# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 dontstopbelieve — Markinho
"""Barra ① Adicionar → ② Converter → ③ Salvar: a etapa atual é clicável e diz o que fazer."""
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
    w.act_auto.setChecked(False)
    yield w
    w.close()


def test_etapa_atual_vira_botao(win, monkeypatch):
    calls = []
    monkeypatch.setattr(win, "add_files_dialog", lambda: calls.append("add"))
    monkeypatch.setattr(win, "convert_queue", lambda sel=False: calls.append("convert"))
    win._update_steps()
    assert "href='add'" in win.steps.text() and "escolher" in win.steps.text()
    win.add_paths([str(ROOT / "exemplos" / "clientes.csv")])
    win._update_steps(pending=True)
    text = win.steps.text()
    assert "href='convert'" in text and "▶" in text and "clique aqui para converter" in text
    win._step_clicked("add")
    win._step_clicked("convert")
    assert calls == ["add", "convert"]


def test_converter_ao_adicionar_ligado_na_primeira_vez(tmp_path, monkeypatch):
    from PySide6.QtCore import QSettings

    from markinho.gui import MainWindow

    QSettings.setPath(QSettings.IniFormat, QSettings.UserScope, str(tmp_path / "novo"))
    QSettings.setDefaultFormat(QSettings.IniFormat)
    monkeypatch.setattr(MainWindow, "DEFAULT_AUTO_CONVERT", True)
    w = MainWindow()
    w.settings.remove("queue/auto")
    w2 = MainWindow()
    assert w2.act_auto.isChecked()
    for x in (w, w2):
        x.close()
