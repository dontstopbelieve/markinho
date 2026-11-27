"""Lembrete de atualização sem internet: a cada ~2 meses, desligável, abre a página só se pedir."""
import datetime as dt

import pytest
from PySide6.QtCore import QSettings

from markinho import updates
from markinho.__main__ import cli

D = dt.date(2026, 1, 1)


@pytest.fixture
def s(tmp_path):
    return QSettings(str(tmp_path / "m.ini"), QSettings.IniFormat)


def test_codigo_fonte_conta_do_primeiro_uso(s, monkeypatch):
    monkeypatch.setattr(updates, "build_date", lambda: None)
    assert not updates.due(s, D)                                  # 1º uso: grava a data, não lembra
    assert not updates.due(s, D + dt.timedelta(days=59))
    assert updates.due(s, D + dt.timedelta(days=60))
    updates.snooze(s, D + dt.timedelta(days=60))
    assert not updates.due(s, D + dt.timedelta(days=100))
    assert updates.due(s, D + dt.timedelta(days=120))
    updates.never(s)
    assert not updates.due(s, D + dt.timedelta(days=400))


def test_versao_antiga_lembra_depois_da_primeira_semana(s, monkeypatch):
    monkeypatch.setattr(updates, "build_date", lambda: D)
    hoje = D + dt.timedelta(days=200)                             # instalou uma versão velha
    assert not updates.due(s, hoje)                              # nunca no 1º dia
    assert updates.due(s, hoje + dt.timedelta(days=7))


def test_data_do_build(tmp_path, monkeypatch):
    assert updates.build_date() is None or isinstance(updates.build_date(), dt.date)


def test_version_mostra_onde_atualizar(capsys):
    assert cli(["--version"]) == 0
    out = capsys.readouterr().out
    assert "Markinho" in out and updates.RELEASES_URL in out and "internet" in out


def test_janela_de_atualizacoes(s, monkeypatch, tmp_path):
    from PySide6 import QtWidgets
    from PySide6.QtGui import QDesktopServices

    from markinho.gui_tools import UpdateDialog

    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    opened = []
    monkeypatch.setattr(QDesktopServices, "openUrl", staticmethod(lambda u: opened.append(u.toString())))
    d = UpdateDialog(None, s, reminder=True)
    d.remind.setChecked(False)
    d.open_page()
    assert opened == [updates.RELEASES_URL]
    assert s.value("updates/never", False, type=bool) and s.value("updates/last_reminder")
