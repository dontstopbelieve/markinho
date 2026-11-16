from markinho.textfix import FixOptions, fix_text


def fx(s, **kw):
    return fix_text(s, FixOptions(**kw) if kw else None)


def test_mojibake():
    t, r = fx("RelatÃ³rio de AvaliaÃ§Ã£o â€” ok")
    assert t == "Relatório de Avaliação — ok" and r.counts["mojibake"] >= 1


def test_latex_accents():
    t, _ = fx("Educa¸c˜ao b´asica e informa¸c˜oes s˜ao p´ublicas")
    assert t == "Educação básica e informações são públicas"


def test_apostrophe_not_touched():
    t, _ = fx("it´s and don´t")
    assert t == "it´s and don´t"


def test_nfd_to_nfc():
    t, r = fx("Café")
    assert t == "Café" and len(t) == 4 and r.counts["accents"] == 1


def test_ligatures_and_invisibles():
    t, _ = fx("ﬁm do ﬂuxo­ pa​lavra﻿")
    assert t == "fim do fluxo palavra"


def test_hyphenation_keeps_compounds():
    t, _ = fx("hifeni-\nzada e Norte-\nAmericano")
    assert t == "hifenizada e Norte-\nAmericano"


def test_entities_and_spaces():
    t, _ = fx("R$ 10 &amp; taxas &#233; &lt;b&gt;")
    assert t == "R$ 10 & taxas é &lt;b&gt;"


def test_cid_and_lost_chars_reported():
    t, r = fx("a(cid:12)b �")
    assert t == "ab �" and r.cid_removed == 1 and r.lost_chars == 1 and len(r.warnings()) == 2


def test_code_blocks_preserved():
    src = "```\nhifeni-\nzada &amp; (cid:1)\n```\n"
    assert fx(src)[0] == src


def test_options_can_disable():
    t, r = fx("ﬁm &amp;", ligatures=False, html_entities=False)
    assert t == "ﬁm &amp;" and r.total == 0


def test_quotes_off_by_default():
    assert fx("“olá”")[0] == "“olá”"
    assert fix_text("“olá”", FixOptions(quotes=True))[0] == '"olá"'
