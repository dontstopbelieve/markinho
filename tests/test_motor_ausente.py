# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 dontstopbelieve — Markinho
"""Motor escolhido que não está instalado (ex.: PyMuPDF4LLM): converte com outro e avisa, sem falhar."""
from pathlib import Path

from markinho.core import convert
from markinho.engines import ENGINES

ROOT = Path(__file__).resolve().parent.parent


def test_motor_nao_instalado_usa_o_automatico(monkeypatch):
    monkeypatch.setattr(ENGINES["pymupdf4llm"], "available", lambda: (False, "não instalado"))
    res = convert(ROOT / "exemplos" / "relatorio.pdf", "pymupdf4llm")
    assert res.markdown.strip()
    assert any("PyMuPDF4LLM" in w and "não está instalado" in w for w in res.warnings)


def test_lista_de_motores_nao_deixa_escolher_o_ausente(monkeypatch, tmp_path):
    from PySide6.QtCore import QSettings

    monkeypatch.setattr(ENGINES["pymupdf4llm"], "available", lambda: (False, "não instalado"))
    from markinho.gui import MainWindow

    s = QSettings(str(tmp_path / "m.ini"), QSettings.IniFormat)
    s.setValue("engine", "pymupdf4llm")                  # configuração antiga
    monkeypatch.setattr("markinho.gui.QSettings", lambda *a, **k: s)
    w = MainWindow()
    panel = w.panel
    assert panel.engine_id() == "auto"
    idx = panel.engine.findData("pymupdf4llm")
    assert idx >= 0 and not panel.engine.model().item(idx).isEnabled()
    w.close()
    w.deleteLater()
