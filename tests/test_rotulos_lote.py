# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 dontstopbelieve — Markinho
"""Rótulos personalizados na lista da anonimização e registro do lote oculto no Windows."""
from markinho.anonymize import AnonOptions, anonymize, clean_label, list_labels

LISTA = "João Pedro\n[empresa]\nAcme Ltda\nBeta S.A.\n[ Local ]\nFazenda Boa Vista\nAcme = [EMPRESA 1]"
TEXTO = "João Pedro trabalha na Acme Ltda (Acme) e na Beta S.A., perto da Fazenda Boa Vista."


def test_cada_rotulo_numera_separado():
    md, rep = anonymize(TEXTO, AnonOptions(words=LISTA))
    assert md == "[NOME 1] trabalha na [EMPRESA 1] ([EMPRESA 1]) e na [EMPRESA 2], perto da [LOCAL 1]."
    assert rep.mapping["[EMPRESA 2]"] == ["Beta S.A."]
    assert list_labels(LISTA) == ["NOME", "EMPRESA", "LOCAL"]


def test_rotulo_limpo_e_modos():
    assert clean_label(" banco 3 [x] ") == "BANCO X"
    md, _ = anonymize(TEXTO, AnonOptions(words=LISTA, mode="marcador"))
    assert "[EMPRESA]" in md and "[LOCAL]" in md
    md, _ = anonymize(TEXTO, AnonOptions(words=LISTA, mode="mascara"))
    assert "Acme Ltda" not in md


def test_janela_novo_rotulo(tmp_path):
    from PySide6.QtCore import QSettings

    from markinho.gui_tools import AnonDialog

    s = QSettings(str(tmp_path / "m.ini"), QSettings.IniFormat)
    d = AnonDialog(None, s, TEXTO, tmp_path / "x.md")
    d.words.setPlainText("João Pedro")
    assert d._new_label("projeto alfa") == "PROJETO ALFA"
    assert d.words.toPlainText() == "João Pedro\n[PROJETO ALFA]\n"
    d.words.insertPlainText("Projeto Netuno")
    assert "[PROJETO ALFA 1]" in d.labels_info.text()
    assert d._new_label("123") == ""                       # só números não vira rótulo
