# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 dontstopbelieve — Markinho
"""Anonimização: endereço, data de nascimento (só o ano), o que ainda identifica e tabela de correspondência."""
import csv
import time

from markinho.anonymize import AnonOptions, anonymize, residual_risks, write_mapping

TEXTO = ("O réu João da Silva, nascido em 12/03/1980, residente na Rua das Flores, 123, apto 12, "
         "CEP 01310-100, com 45 anos. A autora Maria Souza mora na Av. Brasil nº 4500. "
         "Data de nascimento: 5 de maio de 1990. Prazo de 2 anos. O contrato da Rua 7 é antigo.")


def test_endereco_e_nascimento():
    md, rep = anonymize(TEXTO, AnonOptions())
    assert "Rua das Flores" not in md and "Av. Brasil" not in md and "4500" not in md
    assert "12/03/1980" not in md and "maio de 1990" not in md
    assert "[ENDEREÇO 1]" in md and "[NASCIMENTO 2]" in md
    assert "Prazo de 2 anos" in md and "Rua 7" in md          # o que não é dado pessoal fica
    assert rep.counts["endereco"] == 2 and rep.counts["nascimento"] == 2


def test_nascimento_so_o_ano():
    md, _ = anonymize(TEXTO, AnonOptions(birth_year=True))
    assert "nascido em 1980" in md and "nascimento: 1990" in md


def test_avisa_o_que_ainda_identifica():
    _, rep = anonymize(TEXTO, AnonOptions(kinds=["nomes"]))
    assert rep.residual["endereco"] == 2 and rep.residual["nascimento"] == 2
    assert rep.residual["cep"] == 1 and rep.residual["idade"] == 1
    msg = rep.residual_summary()
    assert "Endereço" in msg and "Idade" in msg and "Tirar só o nome não basta" in msg
    _, rep = anonymize(TEXTO, AnonOptions())
    assert set(rep.residual) == {"idade"}                       # com tudo marcado, sobra só a idade
    assert residual_risks("[CPF 1] e [ENDEREÇO 2]", set()) == {}


def test_tabela_de_correspondencia(tmp_path):
    md, rep = anonymize(TEXTO + " Depois, João da Silva voltou.", AnonOptions())
    target = tmp_path / "processo.md"
    target.write_text(md, encoding="utf-8")
    table = write_mapping(target, rep)
    assert table == tmp_path / "processo.correspondencia.csv"
    rows = list(csv.reader(table.read_text(encoding="utf-8-sig").splitlines(), delimiter=";"))
    assert rows[0] == ["Marcador", "Dado original"]
    assert ["[PESSOA 1]", "João da Silva"] in rows and ["[CEP 1]", "01310-100"] in rows
    assert sum(1 for r in rows if r[0] == "[PESSOA 1]") == 1      # a mesma pessoa aparece uma vez só


def test_tabela_nao_executa_formula_e_so_no_modo_pseudonimo(tmp_path):
    _, rep = anonymize("Sua lista", AnonOptions(words="=HYPERLINK(1)", mode="pseudonimo"))
    rep.mapping["[NOME 1]"] = ["=HYPERLINK(\"http://x\")"]
    t = write_mapping(tmp_path / "a.md", rep)
    assert "'=HYPERLINK" in t.read_text(encoding="utf-8-sig")
    _, rep = anonymize(TEXTO, AnonOptions(mode="marcador"))
    assert write_mapping(tmp_path / "b.md", rep) is None and not (tmp_path / "b.correspondencia.csv").exists()


def test_regras_novas_nao_travam_com_texto_preparado():
    ruim = ("Rua " + "Abcdefghij " * 2000 + "\n") * 3 + "nascido em " + "1/" * 5000 + "\n" + "com " + "9" * 5000
    t = time.perf_counter()
    anonymize(ruim, AnonOptions())
    assert time.perf_counter() - t < 5


def test_terminal_grava_a_tabela(tmp_path, capsys):
    from markinho.__main__ import cli

    src = tmp_path / "doc.md"
    src.write_text("# Ata\n\nO réu João da Silva mora na Rua das Flores, 123.\n", encoding="utf-8")
    out = tmp_path / "saida.md"
    assert cli([str(src), "-o", str(out), "--anonimizar-tabela"]) == 0
    assert "João" not in out.read_text(encoding="utf-8")
    assert "João da Silva" in (tmp_path / "saida.correspondencia.csv").read_text(encoding="utf-8-sig")


def test_opcoes_salvas_e_janela(tmp_path, monkeypatch):
    from PySide6.QtCore import QSettings
    from PySide6.QtWidgets import QFileDialog, QMessageBox

    from markinho.gui_tools import AnonDialog
    from markinho.quick import anon_options, save_anon_options

    s = QSettings(str(tmp_path / "m.ini"), QSettings.IniFormat)
    save_anon_options(s, AnonOptions(birth_year=True, save_mapping=True))
    o = anon_options(s)
    assert o.birth_year and o.save_mapping
    dlg = AnonDialog(None, s, TEXTO, tmp_path / "proc.md")
    assert "Endereço" in dlg.found.text() or "ENDEREÇO" in dlg.found.text() or dlg.found.text()
    target = tmp_path / "proc_anon.md"
    monkeypatch.setattr(QFileDialog, "getSaveFileName", lambda *a, **k: (str(target), ""))
    monkeypatch.setattr(QMessageBox, "information", lambda *a, **k: None)
    dlg._accept()
    assert "1980" in target.read_text(encoding="utf-8")           # só o ano
    assert (tmp_path / "proc_anon.correspondencia.csv").is_file()
