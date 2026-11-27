# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 dontstopbelieve — Markinho
"""Idioma do OCR automático: escolhe o idioma instalado pela escrita (OSD) ou pelas palavras do texto."""
import pytest

from markinho import ocr

TEXTOS = {
    "por": "O contrato de locação foi assinado em São Paulo. O locatário não pagará as despesas do condomínio "
           "e também pelo uso da garagem, que são cobradas à parte nos meses de inverno, como está escrito.",
    "spa": "El contrato de arrendamiento se firmó en Madrid y los gastos del inquilino son más altos, pero las "
           "partes están de acuerdo y también sobre el plazo, que es muy largo entre ellas.",
    "fra": "Le contrat a été signé à Paris et les charges sont incluses dans le prix. Le locataire ne paie pas "
           "les frais qui sont avec nous dans ce bail, sur leur demande.",
    "deu": "Der Vertrag wurde in München unterschrieben und die Nebenkosten sind nicht im Preis enthalten. Der "
           "Mieter zahlt die Miete auf das Konto von dem Vermieter, mit einer Frist des Monats.",
    "eng": "The contract was signed in London and the tenant pays the rent at the beginning of each month, which "
           "is due to the landlord for the use of this flat with all that is included by law.",
}


@pytest.mark.parametrize("lang", list(TEXTOS))
def test_adivinha_idioma_latino(lang):
    assert ocr.guess_latin_language(TEXTOS[lang]) == lang


def test_texto_curto_ou_misturado_nao_decide():
    assert ocr.guess_latin_language("Contrato de locação") is None
    assert ocr.guess_latin_language("123 456 789 " * 10) is None


def _data(text):
    return {"text": text.split()}


def test_relê_no_idioma_instalado(monkeypatch):
    monkeypatch.setattr(ocr, "tesseract_languages", lambda: ("por", "eng", "spa", "rus", "chi_sim"))
    monkeypatch.setattr(ocr, "_has_osd", lambda: False)
    assert ocr._auto_language(None, _data(TEXTOS["spa"]), 90) == "spa+eng"
    assert ocr._auto_language(None, _data(TEXTOS["por"]), 90) is None        # português: lê uma vez só


def test_outro_alfabeto_pela_escrita(monkeypatch):
    import pytesseract

    monkeypatch.setattr(ocr, "tesseract_languages", lambda: ("por", "eng", "rus", "chi_sim"))
    monkeypatch.setattr(ocr, "_has_osd", lambda: True)
    for script, want in (("Cyrillic", "rus+eng"), ("Han", "chi_sim")):
        monkeypatch.setattr(pytesseract, "image_to_osd", lambda *a, s=script, **k: {"script": s, "rotate": 0})
        assert ocr._auto_language(None, _data("HoroBop apeHab"), 40) == want


def test_sem_o_pacote_avisa(monkeypatch):
    import pytesseract

    from markinho import core

    monkeypatch.setattr(ocr, "tesseract_languages", lambda: ("por", "eng"))
    monkeypatch.setattr(ocr, "_has_osd", lambda: True)
    monkeypatch.setattr(pytesseract, "image_to_osd", lambda *a, **k: {"script": "Arabic", "rotate": 0})
    avisos = []
    monkeypatch.setattr(core, "warn", lambda msg, *a, **k: avisos.append(msg))
    assert ocr._auto_language(None, _data("Opel! oxy dali]"), 30) is None
    monkeypatch.setattr(ocr, "_has_osd", lambda: False)
    assert ocr._auto_language(None, _data(TEXTOS["deu"]), 90) is None
    assert len(avisos) == 2 and all("Idiomas extras do OCR" in a for a in avisos)


def test_auto_comeca_por_portugues_e_ingles(monkeypatch):
    monkeypatch.setattr(ocr, "tesseract_languages", lambda: ("por", "eng", "spa"))
    assert ocr._tess_lang("auto") == "por+eng"


def test_aviso_repetido_vira_um_so():
    from markinho.core import _NOTES, warn

    notes = []
    tok = _NOTES.set(notes)
    try:
        warn("mesmo aviso", [1])
        warn("mesmo aviso", [3])
        warn("outro", [2])
    finally:
        _NOTES.reset(tok)
    assert notes == [("mesmo aviso", [1, 3]), ("outro", [2])]
