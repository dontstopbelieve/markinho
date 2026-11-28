# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 dontstopbelieve — Markinho
"""Abertura: a instância única é garantida antes de carregar o programa (cliques repetidos não abrem várias
janelas) e o que chega enquanto carrega vai para a janela."""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def test_segundo_clique_enquanto_carrega_nao_abre_outra(monkeypatch):
    import markinho.single as single
    from markinho import __main__ as m

    monkeypatch.delenv("MARKINHO_MULTI", raising=False)
    monkeypatch.setattr(single, "claim", lambda kind, paths, cb: None)     # já existe uma abrindo
    import markinho.gui as g

    monkeypatch.setattr(g, "main", lambda **k: (_ for _ in ()).throw(AssertionError("não devia carregar")))
    assert m.start_gui([]) == 0


def test_o_que_chega_enquanto_carrega_vai_para_a_janela(monkeypatch):
    import markinho.gui as g
    import markinho.single as single
    from markinho import __main__ as m

    monkeypatch.delenv("MARKINHO_MULTI", raising=False)
    got = {}

    def fake_claim(kind, paths, cb):
        cb(["chegou.pdf"])                     # outra instância mandou um arquivo durante o carregamento
        return object()

    monkeypatch.setattr(single, "claim", fake_claim)
    monkeypatch.setattr(g, "main", lambda **k: got.update(k) or 7)
    assert m.start_gui(["a.pdf"]) == 7
    assert got["claimed"] is True and got["early"]["pending"] == ["chegou.pdf"]


def test_janela_recebe_o_que_ficou_pendente(monkeypatch, tmp_path):
    from PySide6.QtCore import QSettings
    from PySide6.QtWidgets import QApplication

    import markinho.gui as g

    QSettings.setPath(QSettings.IniFormat, QSettings.UserScope, str(tmp_path))
    QSettings.setDefaultFormat(QSettings.IniFormat)
    monkeypatch.setenv("MARKINHO_SKIP_WELCOME", "1")
    monkeypatch.setattr(QApplication, "exec", lambda self: 0)
    added = []
    monkeypatch.setattr(g.MainWindow, "add_paths", lambda self, p: added.extend(p))
    early = {"cb": None, "pending": [str(ROOT / "exemplos" / "clientes.csv")]}
    monkeypatch.setattr("sys.argv", ["markinho"])
    assert g.main(listener=None, early=early, claimed=True) == 0
    assert added == [str(ROOT / "exemplos" / "clientes.csv")] and callable(early["cb"])
    for w in QApplication.topLevelWidgets():
        w.close()
