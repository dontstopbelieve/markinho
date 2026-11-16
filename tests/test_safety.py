"""Arquivos maliciosos: bomba de compressão, partes gigantes, páginas enormes, nomes e extensões."""
import io
import zipfile

import pytest

from markinho import convert
from markinho.assets import AssetSink
from markinho.core import ConversionError
from markinho.naming import validate
from markinho.safety import UnsafeFileError, check_zip, read_zip_member, safe_resolution


def _zip(path, entries):
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as zf:
        for name, data in entries.items():
            zf.writestr(name, data)
    return path


def test_zip_bomb_is_refused_before_opening(tmp_path):
    # 40 MB de zeros viram ~40 KB compactados: expansão ~1000×
    bomb = _zip(tmp_path / "relatorio.docx", {"word/document.xml": b"\0" * (40 * 1024 ** 2)})
    with pytest.raises(UnsafeFileError):
        check_zip(bomb)
    with pytest.raises(ConversionError, match="segurança"):
        convert(bomb)


def test_normal_office_file_passes(tmp_path):
    from pathlib import Path

    check_zip(Path(__file__).resolve().parent.parent / "exemplos" / "relatorio.docx")
    check_zip(tmp_path / "nao_existe.zip")                 # não é ZIP: não faz nada


def test_read_zip_member_caps_size():
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("a.txt", b"x" * 5000)
    with zipfile.ZipFile(buf) as zf:
        assert len(read_zip_member(zf, "a.txt", limit=5000)) == 5000
        with pytest.raises(UnsafeFileError):
            read_zip_member(zf, "a.txt", limit=1000)


def test_huge_pdf_page_resolution_is_limited():
    assert safe_resolution(595, 842, 300) == 300               # A4: resolução pedida
    giant = safe_resolution(200 * 72, 200 * 72, 300)            # página de 200 × 200 polegadas
    assert (200 * giant) ** 2 <= 40_000_000 * 1.01


def test_asset_extension_from_document_is_sanitized():
    sink = AssetSink("doc_assets")
    ref = sink.add(b"MZ\x90\x00 fake", ".exe")
    assert ref.endswith(".png)") and all(k.endswith(".png") for k in sink.files)


def test_nested_template_fields_are_rejected():
    assert validate("{n:{nome}}")
    assert validate("{nome.__class__}")
    assert validate("{n}_{nome}") is None


@pytest.mark.parametrize("make", [
    lambda n: ("chunk", "# " + "a" + " " * n + "b\n\ntexto"),
    lambda n: ("san", "<img " + "src='" * n),
    lambda n: ("san", "<script>" * n),
    lambda n: ("san", "<a" + " " * n + "onx"),
    lambda n: ("llm", "<!--" * n),
])
def test_no_slow_regex_on_crafted_text(make):
    """Textos preparados para travar expressões regulares precisam terminar rápido."""
    import time

    from markinho.chunker import chunk_markdown
    from markinho.postprocess import apply_profile
    from markinho.sanitize import sanitize_markdown

    kind, text = make(100_000)
    t = time.time()
    if kind == "chunk":
        chunk_markdown(text, 1500, 100, "title")
    elif kind == "san":
        sanitize_markdown(text)
    else:
        apply_profile(text, "llm")
    assert time.time() - t < 3


def test_describe_only_local_ollama():
    from markinho.describe import _request

    with pytest.raises(ValueError):
        _request("http://exemplo.com:11434/api/tags")
