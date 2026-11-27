"""Um único QApplication para todos os testes (criar e destruir aplicações do Qt entre testes
derruba o processo)."""
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ["MARKINHO_LANG"] = "pt"          # os testes conferem os textos em português

from PySide6.QtWidgets import QApplication  # noqa: E402

_APP = QApplication.instance() or QApplication([])
