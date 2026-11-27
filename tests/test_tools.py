"""Colar e converter, Copiar para IA, ABNT, dividir por títulos, relatório do lote, diagnóstico e
pasta monitorada."""
import shutil
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))
from markinho import aitools, paste, report, splitter  # noqa: E402

EX = Path(__file__).resolve().parent.parent / "exemplos"


def test_paste_html_and_text():
    md, src = paste.clipboard_to_markdown(
        html="<h2>Título</h2><p>Um <b>negrito</b> e <a href='https://a.b'>link</a>.</p>"
             "<table><tr><th>A</th><th>B</th></tr><tr><td>1</td><td>2</td></tr></table>")
    assert src == "texto formatado" and "## Título" in md and "**negrito**" in md and "| A | B |" in md
    md, src = paste.clipboard_to_markdown(text="linha 1\r\nlinha 2")
    assert src == "texto" and md.strip() == "linha 1\nlinha 2"
    assert paste.clipboard_to_markdown() == ("", "")


def test_paste_image_runs_ocr():
    from markinho.ocr import available_backends

    if "tesseract" not in available_backends():
        pytest.skip("sem Tesseract")
    import io

    from PIL import Image, ImageDraw, ImageFont

    im = Image.new("RGB", (900, 160), "white")
    ImageDraw.Draw(im).text((20, 50), "Relatório de Ação", fill="black",
                            font=ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 48))
    buf = io.BytesIO()
    im.save(buf, "PNG")
    md, src = paste.clipboard_to_markdown(image_png=buf.getvalue())
    assert src == "imagem (OCR)" and "Relatório de Ação" in md and md.startswith("# Imagem colada")


def test_ai_tokens_and_split():
    md = "\n\n".join(f"# Capítulo {i}\n\n" + ("Texto do capítulo com várias palavras. " * 120) for i in range(1, 9))
    assert aitools.estimate_tokens("a" * 36) == 10
    parts = aitools.split_for_ai(md, 2_000)
    assert len(parts) > 1 and parts[0].startswith("[Parte 1 de") and "última parte" in parts[-1]
    assert all(aitools.estimate_tokens(p) <= 2_000 for p in parts)
    assert aitools.split_for_ai(md, 0) == [md]
    assert "![" not in aitools.prepare("# T\n\n![img](a.png)\n\ntexto <!-- c -->")


def test_split_by_headings_ignores_code():
    md = "intro\n\n# Um\n\ntexto\n\n```\n# não é título\n```\n\n## Sub\n\n# Dois\n\nfim\n"
    parts = splitter.split_by_headings(md, 1)
    assert [t for t, _ in parts] == ["Início", "Um", "Dois"] and "# não é título" in parts[1][1]
    assert [t for t, _ in splitter.split_by_headings(md, 2)] == ["Início", "Um", "Sub", "Dois"]


def test_batch_report(tmp_path):
    from markinho import convert

    r = convert(EX / "relatorio.docx")
    rows = [report.row(str(EX / "relatorio.docx"), r), report.row("/x/quebrado.pdf", error="falhou"),
            report.row("/x/espera.pdf", queued=True)]
    report.to_csv(rows, tmp_path / "r.csv")
    report.to_html(rows, tmp_path / "r.html")
    csv_text = (tmp_path / "r.csv").read_text(encoding="utf-8-sig")
    assert csv_text.startswith("Arquivo;Pasta;Situação") and "quebrado.pdf" in csv_text and "Na fila" in csv_text
    assert "<script" not in (tmp_path / "r.html").read_text(encoding="utf-8")
    assert report.summary(rows).startswith("3 arquivo(s): 1 convertido(s)")


def test_abnt_docx_native(tmp_path):
    import docx

    from markinho.exporter import export

    export("# Introdução\n\nTexto.\n\n## Objetivo\n\n> Citação longa.\n", tmp_path / "t.docx", "docx",
           {"template": "abnt", "number_sections": True}, backend="native")
    d = docx.Document(str(tmp_path / "t.docx"))
    sec = d.sections[0]
    assert round(sec.top_margin.cm, 1) == 3.0 and round(sec.right_margin.cm, 1) == 2.0
    assert d.styles["Normal"].font.name == "Times New Roman"
    assert [p.text for p in d.paragraphs][:3] == ["1 Introdução", "Texto.", "1.1 Objetivo"]
    assert "PAGE" in sec.header._element.xml


def test_diagnostics_report_has_no_paths(tmp_path, monkeypatch):
    from PySide6.QtCore import QSettings

    from markinho import diagnostics

    monkeypatch.setattr(Path, "home", staticmethod(lambda: Path("/home/fulano")))
    diagnostics.record_error("/home/fulano/Documentos/contrato secreto.pdf", "falhou ao ler")
    s = QSettings(str(tmp_path / "s.ini"), QSettings.IniFormat)
    s.setValue("engine", "auto")
    s.setValue("last_dir", "/home/fulano/Documentos")
    text = diagnostics.report_text(s)
    assert "contrato secreto.pdf" in text and "falhou ao ler" in text and "/home/fulano/Documentos" not in text
    assert "engine = auto" in text and "last_dir" not in text and "Motores" in text


def test_watch_folder_converts_new_files_only(tmp_path, monkeypatch):
    from PySide6.QtCore import QCoreApplication

    from markinho.watch import FolderWatcher, candidates

    app = QCoreApplication.instance() or QCoreApplication([])
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "cfg"))
    inbox, out = tmp_path / "entrada", tmp_path / "saida"
    inbox.mkdir()
    shutil.copy(EX / "relatorio.docx", inbox / "antigo.docx")
    w = FolderWatcher(inbox, out)
    got = []
    w.converted.connect(got.append)
    assert w.start()
    shutil.copy(EX / "relatorio.docx", inbox / "novo.docx")
    (inbox / "nota.md").write_text("# já é markdown")
    import time

    deadline = time.time() + 30
    while not got and time.time() < deadline:
        w.scan()
        app.processEvents()
        time.sleep(0.2)
    w.stop()
    assert [r.source.name for r in got] == ["novo.docx"] and not got[0].error
    assert (out / "novo.md").is_file() and not (out / "antigo.md").exists()
    assert "nota.md" not in {Path(p).name for p in candidates(inbox)}
    # retomar: o que chegou com o Markinho fechado é convertido ao abrir; o antigo continua ignorado
    shutil.copy(EX / "relatorio.docx", inbox / "chegou_fechado.docx")
    w2 = FolderWatcher(inbox, out)
    got.clear()
    w2.converted.connect(got.append)
    assert w2.start()
    deadline = time.time() + 30
    while not got and time.time() < deadline:
        w2.scan()
        app.processEvents()
        time.sleep(0.2)
    w2.stop()
    assert [r.source.name for r in got] == ["chegou_fechado.docx"]
    assert not (out / "antigo.md").exists() and not (out / "novo_2.md").exists()


def test_diagnostics_hides_windows_user_name():
    from markinho.diagnostics import _redact

    msg = r"""Error opening data file "C:\\Users\\USUARIOX\\Desktop\\Markinho\\tessdata_best"/por.traineddata"""
    out = _redact(msg)
    assert "USUARIOX" not in out and "Desktop" in out
    assert "Detal" not in _redact("C:/Users/Fulano Detal/x.pdf")
    assert "fulano" not in _redact("/home/fulano/x.pdf")


def test_diagnostics_report_has_setup_system_and_hides_names(tmp_path):
    from PySide6.QtCore import QSettings

    from markinho import diagnostics

    diagnostics.record_error("/home/fulano/Documentos/balanço sigiloso.pdf", "motor travou", "Traceback: x",
                             {"motor": "docling", "opções do motor": {"ocr": True, "pasta": "/home/fulano/x"}})
    s = QSettings(str(tmp_path / "s.ini"), QSettings.IniFormat)
    text = diagnostics.report_text(s)
    assert "balanço sigiloso.pdf" in text and "motor: docling" in text and "Traceback: x" in text
    assert "/home/fulano/x" not in text
    info = diagnostics.system_info()
    assert any("Sistema" in line or "sistema" in line for line in info)
    hidden = diagnostics.report_text(s, hide_names=True)
    assert "balanço sigiloso" not in hidden and "arquivo" in hidden and "motor: docling" in hidden


def test_privacy_doc_matches_app_text():
    from markinho.privacy import TEXT

    assert (Path(__file__).resolve().parents[1] / "PRIVACIDADE.md").read_text(encoding="utf-8") == TEXT
