from markinho import edition


def test_source_run_has_no_edition():
    assert edition.current() is None and edition.label() == "código-fonte"
    assert edition.upgrade_hint("docling") == ""


def test_marker_and_hints(tmp_path, monkeypatch):
    marker = tmp_path / "edition.txt"
    monkeypatch.setattr(edition, "_marker", lambda: marker)
    marker.write_text("leve")
    assert edition.current() is edition.LEVE
    assert "PADRÃO" in edition.upgrade_hint("pandoc") and "COMPLETA" in edition.upgrade_hint("docling")
    marker.write_text("padrao")
    assert edition.upgrade_hint("pandoc") == "" and "COMPLETA" in edition.upgrade_hint("docling")
    marker.write_text("completa")
    assert edition.upgrade_hint("docling") == ""


def test_editions_are_cumulative():
    assert set(edition.LEVE.features) < set(edition.PADRAO.features) < set(edition.COMPLETA.features)
