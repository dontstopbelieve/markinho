# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 dontstopbelieve — Markinho
"""Idiomas: todo texto marcado com tr() tem tradução em inglês e espanhol, com os mesmos marcadores {0}."""
import ast
import json
import re
from pathlib import Path

import pytest

from markinho import i18n

PKG = Path(i18n.__file__).resolve().parent
CATALOGS = {lang: json.loads((PKG / "locale" / f"{lang}.json").read_text(encoding="utf-8")) for lang in ("en", "es")}
EN = CATALOGS["en"]


def _keys() -> dict[str, str]:
    keys: dict[str, str] = {}
    for f in sorted(PKG.glob("*.py")):
        for node in ast.walk(ast.parse(f.read_text(encoding="utf-8"))):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "tr" \
                    and node.args and isinstance(node.args[0], ast.Constant) and isinstance(node.args[0].value, str):
                keys.setdefault(node.args[0].value, f.name)
    return keys


def _marks(s: str) -> list[str]:
    return sorted(re.findall(r"\{[^{}]*\}", s))


@pytest.mark.parametrize("lang", sorted(CATALOGS))
def test_todo_texto_tem_traducao(lang):
    faltando = {k: f for k, f in _keys().items() if k not in CATALOGS[lang]}
    assert not faltando, f"sem tradução em locale/{lang}.json: {list(faltando.items())[:10]}"


@pytest.mark.parametrize("lang", sorted(CATALOGS))
def test_traducoes_mantem_marcadores(lang):
    ruins = [k for k, v in CATALOGS[lang].items() if _marks(k) != _marks(v) or k.count("\n") != v.count("\n")]
    assert not ruins, ruins[:10]


def test_todo_idioma_da_lista_tem_catalogo():
    for code, _label in i18n.LANGUAGES:
        if code not in ("auto", "pt"):
            assert code in CATALOGS and i18n._load(code), code


def test_tr_so_aceita_texto_literal():
    """tr(variável) não entra no catálogo: o texto ficaria sem tradução sem ninguém perceber."""
    for f in sorted(PKG.glob("*.py")):
        if f.name == "i18n.py":
            continue
        for node in ast.walk(ast.parse(f.read_text(encoding="utf-8"))):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "tr":
                assert node.args and isinstance(node.args[0], ast.Constant), f"{f.name}:{node.lineno}"


def test_codigos_internos_nao_sao_traduzidos():
    """Nomes de pacote, valores de opção e sinais (“auto”, “leve”, “,”) não podem passar por tr()."""
    ruins = [k for k in _keys() if re.fullmatch(r"[a-z_0-9]+|[^A-Za-zÀ-ú]{0,3}", k)]
    assert not ruins, ruins


def test_trocar_idioma():
    try:
        i18n.set_language_for_tests("en")
        assert i18n.language() == "en"
        assert i18n.tr("Converter") != "Converter"
        assert i18n.tr("texto que não existe no catálogo") == "texto que não existe no catálogo"
        i18n.set_language_for_tests("pt")
        assert i18n.tr("Converter") == "Converter"
    finally:
        i18n.set_language_for_tests("pt")


def test_idioma_pela_variavel(monkeypatch):
    monkeypatch.setenv("MARKINHO_LANG", "en_US")
    assert i18n._detect() == "en"
    monkeypatch.setenv("MARKINHO_LANG", "es_AR")
    assert i18n._detect() == "es"
    monkeypatch.setenv("MARKINHO_LANG", "")
    assert i18n._detect() in ("pt", "en")
    assert i18n._load("xx") == {}


def test_catalogo_sem_sobras():
    """Texto removido do código sai também do catálogo (evita traduções velhas acumuladas)."""
    keys = _keys()
    for lang, cat in CATALOGS.items():
        sobras = [k for k in cat if k not in keys]
        assert not sobras, (lang, sobras[:10])


def test_privacidade_no_idioma():
    from markinho import privacy

    try:
        i18n.set_language_for_tests("en")
        assert privacy.text() is privacy.TEXT_EN and "stay on your computer" in privacy.text()
        i18n.set_language_for_tests("es")
        assert privacy.text() is privacy.TEXT_ES and "se quedan en su equipo" in privacy.text()
        i18n.set_language_for_tests("pt")
        assert privacy.text() is privacy.TEXT
    finally:
        i18n.set_language_for_tests("pt")
    # as duas versões têm as mesmas seções
    assert privacy.TEXT.count("\n## ") == privacy.TEXT_EN.count("\n## ") == privacy.TEXT_ES.count("\n## ")


def test_numero_no_idioma():
    try:
        i18n.set_language_for_tests("en")
        assert i18n.num(1234567) == "1,234,567"
        i18n.set_language_for_tests("es")
        assert i18n.num(1234567) == "1.234.567"
        assert i18n.tr("Converter") == "Convertir"
    finally:
        i18n.set_language_for_tests("pt")
    assert i18n.num(1234567) == "1.234.567"


def test_situacao_do_relatorio_nao_depende_do_idioma():
    from markinho import report

    rows = [report.row("/x/a.pdf", error="falhou"), report.row("/x/b.pdf", queued=True)]
    assert [r["estado"] for r in rows] == ["erro", "fila"]
    assert report.summary(rows).startswith("2 ")
