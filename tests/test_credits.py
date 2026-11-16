"""Créditos e licenças: todo componente incluído tem crédito; textos de licença disponíveis."""
import os

import pytest

from markinho.credits import DISCLAIMER, INCLUDED, INSPIRED_BY, included_here, license_files


def test_credit_entries_complete():
    for c in INCLUDED + INSPIRED_BY:
        assert c.name and c.author and c.url.startswith("http") and c.role
    names = {c.name for c in INCLUDED}
    for must in ("Qt / PySide6", "Pandoc", "AnyDoc", "Tesseract OCR", "Docling", "MCP Python SDK"):
        assert must in names
    assert "independente" in DISCLAIMER and "sem copiar código" in DISCLAIMER


def test_excluded_projects_are_only_inspiration():
    included = {c.name.lower() for c in INCLUDED}
    for name in ("marker", "pymupdf4llm"):            # licenças restritivas: nunca incluídos
        assert not any(name in n for n in included)


def test_presence_and_license_texts():
    present = dict((c.name, here) for c, here in included_here())
    assert present["Python"] and present["Qt / PySide6"]
    files = license_files()
    assert files and any("LGPL" in rel or "lgpl" in text.lower()[:2000] for _, rel, text in files)


def test_bundled_license_texts_in_repo():
    from pathlib import Path

    d = Path(__file__).resolve().parent.parent / "licenses"
    for f in ("LGPL-3.0-only.txt", "GPL-3.0-only.txt", "MIT.txt", "Apache-2.0.txt", "BSD-3-Clause.txt",
              "CDLA-Permissive-2.0.txt", "AnyDoc-MIT.txt"):
        assert (d / f).stat().st_size > 500, f


def test_about_dialog_tabs():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    QtWidgets = pytest.importorskip("PySide6.QtWidgets")
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    from markinho.gui import AboutDialog, MainWindow

    w = MainWindow()
    d = AboutDialog(w, 2)
    tabs = d.findChild(QtWidgets.QTabWidget)
    assert [tabs.tabText(i).split(" (")[0] for i in range(tabs.count())] == ["Sobre", "Créditos", "Licenças"]
    assert "Ajuda" in [a.text() for a in w.menuBar().actions()]
    d.close()
    w.close()


def test_termos_rtf_somente_ascii():
    """O WiX (instalador .msi) recusa caracteres fora da página 1252: o RTF usa só escapes \\uNNNN?."""
    from pathlib import Path

    data = (Path(__file__).resolve().parent.parent / "packaging" / "windows" / "termos.rtf").read_bytes()
    assert all(b < 128 for b in data)


def test_project_license_is_agpl():
    from pathlib import Path

    root = Path(__file__).resolve().parent.parent
    assert "GNU AFFERO GENERAL PUBLIC LICENSE" in (root / "LICENSE").read_text(encoding="utf-8")
    assert 'license = "AGPL-3.0-only"' in (root / "pyproject.toml").read_text(encoding="utf-8")
    missing = [p.name for p in (root / "markinho").rglob("*.py")
               if "SPDX-License-Identifier: AGPL-3.0-only" not in p.read_text(encoding="utf-8")[:300]]
    assert not missing, missing
