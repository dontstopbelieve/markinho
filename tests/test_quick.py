"""Botão direito do Windows: “Converter para Markdown aqui” e instância única."""
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
from PySide6.QtCore import QCoreApplication, QSettings

from markinho.quick import convert_here, summary
from markinho.single import Listener, channel_name, forward

EX = Path(__file__).resolve().parent.parent / "exemplos"


def _settings(tmp_path, **values) -> QSettings:
    s = QSettings(str(tmp_path / "markinho.ini"), QSettings.IniFormat)
    for k, v in values.items():
        s.setValue(k.replace("__", "/"), v)
    s.sync()
    return s


def test_convert_here_writes_next_to_original(tmp_path):
    src = shutil.copy(EX / "relatorio.docx", tmp_path / "Relatório Final.docx")
    s = _settings(tmp_path)
    r = convert_here(src, s)
    assert not r.error and r.output == tmp_path / "Relatório Final.md"
    assert r.output.read_text(encoding="utf-8").strip()
    # de novo: não sobrescreve (padrão "acrescentar _2")
    r2 = convert_here(src, s)
    assert r2.output.name == "Relatório Final_2.md"
    assert summary([r, r2])[1].startswith("2 arquivo(s) convertido(s)")


def test_convert_here_uses_saved_naming_and_skip(tmp_path):
    src = shutil.copy(EX / "relatorio.docx", tmp_path / "relatorio.docx")
    s = _settings(tmp_path, naming__template="{n}_{nome}", naming__conflict="skip", naming__digits=2)
    assert convert_here(src, s, index=0).output.name == "01_relatorio.md"
    assert convert_here(src, s, index=1).output.name == "02_relatorio.md"
    again = convert_here(src, s, index=0)
    assert again.skipped and "pulado" in summary([again])[1]


def test_convert_here_errors_are_reported(tmp_path, monkeypatch):
    import markinho.core
    from markinho.core import ConversionError

    s = _settings(tmp_path)
    r = convert_here(tmp_path / "nao_existe.pdf", s)
    assert r.error == "arquivo não encontrado" and r.output is None
    bad = tmp_path / "quebrado.docx"
    bad.write_bytes(b"isto nao e um docx")

    def falha(*a, **k):
        raise ConversionError("nenhum motor conseguiu ler o arquivo")

    monkeypatch.setattr(markinho.core, "convert", falha)
    r = convert_here(bad, s)
    assert r.error and not list(tmp_path.glob("*.md"))
    assert summary([r])[0] == "Markinho: terminou com erros"


def test_single_instance_forwards_paths(tmp_path):
    app = QCoreApplication.instance() or QCoreApplication([])
    got: list[str] = []
    name = channel_name(f"teste-{os.getpid()}")
    lis = Listener(name, got.extend)
    assert lis.listen()
    assert forward(name, ["a.pdf", "b.docx"])
    for _ in range(50):
        app.processEvents()
        if got:
            break
    lis.server.close()
    assert got == ["a.pdf", "b.docx"]
    assert not forward(name, ["c.pdf"], 300)          # ninguém escutando: esta instância segue sozinha


@pytest.mark.skipif(sys.platform == "win32", reason="isolamento das configurações usa XDG")
def test_quick_command_end_to_end(tmp_path):
    src = shutil.copy(EX / "relatorio.docx", tmp_path / "relatorio.docx")
    env = dict(os.environ, QT_QPA_PLATFORM="offscreen", XDG_CONFIG_HOME=str(tmp_path / "cfg"), MARKINHO_QUIET="1")
    p = subprocess.run([sys.executable, "-m", "markinho", "--converter-aqui", str(src)], env=env,
                       capture_output=True, text=True, timeout=120)
    assert p.returncode == 0, p.stderr
    assert (tmp_path / "relatorio.md").is_file()


@pytest.mark.skipif(sys.platform == "win32", reason="isolamento das configurações usa XDG")
def test_quick_many_files_at_once(tmp_path):
    """Seleção múltipla: o Windows abre uma instância por arquivo, quase ao mesmo tempo."""
    files = [shutil.copy(EX / "relatorio.docx", tmp_path / f"doc{i}.docx") for i in range(5)]
    env = dict(os.environ, QT_QPA_PLATFORM="offscreen", XDG_CONFIG_HOME=str(tmp_path / "cfg"), MARKINHO_QUIET="1")
    procs = [subprocess.Popen([sys.executable, "-m", "markinho", "--converter-aqui", str(f)], env=env,
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE) for f in files]
    for p in procs:
        assert p.wait(timeout=180) == 0
    assert sorted(x.name for x in tmp_path.glob("*.md")) == [f"doc{i}.md" for i in range(5)]


def test_convert_to_chosen_target_and_export(tmp_path):
    from markinho.quick import default_target, export_one

    src = shutil.copy(EX / "relatorio.docx", tmp_path / "relatorio.docx")
    s = _settings(tmp_path)
    assert default_target(Path(src), s) == tmp_path / "relatorio.md"
    dest = tmp_path / "escolhido" / "meu nome.md"
    r = convert_here(src, s, target=dest)
    assert not r.error and r.output == dest and dest.read_text(encoding="utf-8").strip()
    out = export_one(dest, "html", tmp_path / "saida.html")
    assert not out.error and "<h1" in (tmp_path / "saida.html").read_text(encoding="utf-8")
    abnt = export_one(dest, "docx", tmp_path / "abnt.docx", {"template": "abnt", "number_sections": True})
    assert not abnt.error and (tmp_path / "abnt.docx").stat().st_size > 1000
    assert "não encontrado" in export_one(tmp_path / "x.md", "html", tmp_path / "y.html").error


def test_convert_here_reports_page_progress(tmp_path):
    import sys

    sys.path.insert(0, str(Path(__file__).parent))
    from make_pdf import make_pdf

    pdf = make_pdf(tmp_path / "longo.pdf", pages=4)
    seen = []
    r = convert_here(pdf, _settings(tmp_path), progress=lambda d, t: seen.append((d, t)))
    assert not r.error and seen and seen[-1] == (4, 4)
