"""Limpeza do Markdown antes de exportar: sem downloads, sem scripts, código intacto."""
from markinho.exporter import export
from markinho.sanitize import sanitize_markdown


def test_scripts_and_events_removed_outside_code():
    md = ("Texto <b onclick=\"roubar()\">negrito</b> <a href=\"javascript:alert(1)\">x</a>\n\n"
          "<script>alert('oi')</script>\n<iframe src=\"https://a\"></iframe>\n\n"
          "```html\n<script>exemplo()</script>\n```\n")
    out, notes = sanitize_markdown(md)
    assert "onclick" not in out and "javascript:" not in out and "<iframe" not in out
    assert "alert('oi')" not in out
    assert "<script>exemplo()</script>" in out           # dentro do bloco de código: intacto
    assert notes


def test_remote_images_become_links_local_kept(tmp_path):
    md = "![a](https://site/x.png) ![b](//cdn/y.png) ![c](doc_assets/imagem_001.png) ![d](data:image/png;base64,AA)"
    out, _ = sanitize_markdown(md, tmp_path)
    assert "![a]" not in out and "[a](https://site/x.png)" in out and "[b](//cdn/y.png)" in out
    assert "![c](doc_assets/imagem_001.png)" in out and "![d](data:image/png;base64,AA)" in out


def test_allowed_dirs_blocks_outside_images(tmp_path):
    inside = tmp_path / "pasta"
    inside.mkdir()
    md = f"![x]({tmp_path / 'fora.png'}) ![y](ok.png) ![z](../fora2.png)"
    out, _ = sanitize_markdown(md, inside, [inside])
    assert "fora.png" not in out and "fora2.png" not in out and "![y](ok.png)" in out


def test_native_html_export_has_no_script(tmp_path):
    export("# T\n\n<script>x()</script>\n\n<p onmouseover='y()'>p</p>", tmp_path / "a.html", "html",
           backend="native")
    html = (tmp_path / "a.html").read_text(encoding="utf-8")
    assert "<script>x()" not in html and "onmouseover" not in html
