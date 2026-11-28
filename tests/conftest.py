"""Um único QApplication para todos os testes (criar e destruir aplicações do Qt entre testes
derruba o processo)."""
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ["MARKINHO_LANG"] = "pt"          # os testes conferem os textos em português

from PySide6.QtWidgets import QApplication  # noqa: E402

_APP = QApplication.instance() or QApplication([])

import pytest  # noqa: E402


@pytest.fixture(autouse=True)
def _janela_no_modo_completo(monkeypatch):
    """Os testes da janela foram escritos para o modo Completo; os do Simples trocam de modo de propósito."""
    from PySide6.QtCore import QSettings

    from markinho.gui import MainWindow

    monkeypatch.setattr(MainWindow, "DEFAULT_MODE", "complete")
    monkeypatch.setattr(MainWindow, "DEFAULT_AUTO_CONVERT", False)    # testes da fila contam com ela parada
    QSettings("Markinho", "Markinho").remove("queue/auto")
    QSettings("Markinho", "Markinho").remove("ui/mode")      # o último modo não passa de um teste para outro
