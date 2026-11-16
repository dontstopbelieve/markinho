import datetime as dt

from markinho.naming import NameContext, NamingOptions, plan, rename_assets, render, slugify, validate

D = dt.date(2026, 11, 13)


def ctx(stem, **kw):
    return NameContext(stem, kw.pop("original", stem + ".pdf"), date=D, **kw)


def test_keep_name_and_extension():
    assert [p.name for p in plan([ctx("contrato")], NamingOptions())] == ["contrato.md"]
    assert plan([ctx("contrato")], NamingOptions(ext=".txt"))[0].name == "contrato.txt"


def test_numbering_follows_order():
    names = [p.name for p in plan([ctx("b"), ctx("a"), ctx("c")], NamingOptions("{n}_{nome}"))]
    assert names == ["001_b.md", "002_a.md", "003_c.md"]
    o = NamingOptions("{n} - {nome}", start=10, digits=2)
    assert render(ctx("x"), 0, o) == "10 - x"
    assert render(ctx("x"), 4, NamingOptions("{n:04}_{nome}")) == "0005_x"


def test_tokens():
    c = ctx("rel", title="Relatório Anual", folder="Clientes", engine="native", original="rel.docx")
    assert render(c, 0, NamingOptions("{data}_{titulo}")) == "2026-11-13_Relatório Anual"
    assert render(c, 0, NamingOptions("{pasta}-{original}-{motor}")) == "Clientes-rel.docx-native"


def test_custom_rename_and_safe_names():
    c = ctx("x", custom="Contrato de Locação: Final?")
    assert render(c, 0, NamingOptions()) == "Contrato de Locação_ Final"
    assert render(c, 0, NamingOptions(safe=True)) == "contrato-de-locacao-final"
    assert slugify("Relatório  Final (v2).PDF") == "relatorio-final-v2.pdf"


def test_invalid_template_and_reserved():
    assert validate("{nome}") is None and "desconhecido" in validate("{nomee}") and validate("") is not None
    assert render(ctx("x"), 0, NamingOptions("{nomee}")) == "x"          # padrão inválido: mantém o nome
    assert render(ctx("CON"), 0, NamingOptions()) == "_CON"              # nome reservado do Windows


def test_conflicts(tmp_path):
    (tmp_path / "a.md").write_text("x")
    o = NamingOptions()
    assert plan([ctx("a"), ctx("a")], o, tmp_path)[0].name == "a_2.md"   # existe no disco
    assert [p.name for p in plan([ctx("a"), ctx("a")], o)] == ["a.md", "a_2.md"]   # repetido no lote
    assert plan([ctx("a")], NamingOptions(conflict="overwrite"), tmp_path)[0].action == "overwrite"
    assert plan([ctx("a")], NamingOptions(conflict="skip"), tmp_path)[0].action == "skip"


def test_rename_assets():
    md = "![x](contrato_assets/imagem_001.png) e ![[imagem_001.png]]"
    new_md, files = rename_assets(md, {"contrato_assets/imagem_001.png": b"1"}, "001_contrato")
    assert "](001_contrato_assets/imagem_001.png)" in new_md and "![[imagem_001.png]]" in new_md
    assert list(files) == ["001_contrato_assets/imagem_001.png"]


def test_rename_assets_with_spaces(tmp_path):
    from markinho.assets import write_assets

    md, files = rename_assets("![](x_assets/imagem_001.png)", {"x_assets/imagem_001.png": b"1"}, "003_Contrato Antigo")
    assert "](003_Contrato_Antigo_assets/imagem_001.png)" in md
    assert write_assets(md, files, tmp_path) == 1 and (tmp_path / "003_Contrato_Antigo_assets" / "imagem_001.png").is_file()
