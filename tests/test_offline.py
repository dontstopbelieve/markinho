"""Sigilo verificado: o Markinho funciona com a internet bloqueada e nunca tenta se conectar.

Cada teste roda com a rede bloqueada dentro do Python (qualquer tentativa de conexão é registrada e falha).
No GitHub, este arquivo roda também numa máquina SEM rede nenhuma (``unshare -rn``), o que pega até
programas externos (Pandoc, Tesseract). Se um dia alguma parte do Markinho tentar acessar a internet,
o teste falha e a versão não sai.
"""
import shutil
import socket
from pathlib import Path

import pytest

from markinho.core import convert
from markinho.postprocess import OutputOptions

ROOT = Path(__file__).resolve().parent.parent
EXEMPLOS = sorted(p for p in (ROOT / "exemplos").iterdir() if p.is_file())
ANTIGOS = sorted(p for p in (ROOT / "tests" / "fixtures").iterdir() if p.is_file())


@pytest.fixture(autouse=True)
def sem_internet(monkeypatch):
    """Toda tentativa de conexão de rede é anotada e recusada."""
    tentativas = []

    def bloqueia(*a, **k):
        tentativas.append(a[1:2] or a[:1])
        raise OSError("rede bloqueada pelo teste de sigilo")

    monkeypatch.setattr(socket.socket, "connect", bloqueia)
    monkeypatch.setattr(socket.socket, "connect_ex", bloqueia)
    monkeypatch.setattr(socket, "create_connection", bloqueia)
    monkeypatch.setattr(socket, "getaddrinfo", bloqueia)
    yield tentativas
    assert not tentativas, f"o Markinho tentou acessar a rede: {tentativas}"


@pytest.mark.parametrize("arquivo", EXEMPLOS + ANTIGOS, ids=lambda p: p.name)
def test_converte_sem_internet(arquivo, tmp_path):
    src = tmp_path / arquivo.name
    shutil.copy(arquivo, src)
    res = convert(src, "auto")
    assert res.markdown.strip()


def test_escaneado_com_ocr_sem_internet(tmp_path):
    from markinho import ocr

    if ocr.pick_backend("auto") is None:
        pytest.skip("sem OCR instalado")
    from PIL import Image, ImageDraw, ImageFont

    img = Image.new("RGB", (1240, 400), "white")
    draw = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype("DejaVuSans.ttf", 48)
    except OSError:
        font = ImageFont.load_default()
    draw.text((60, 120), "Contrato sigiloso de teste", fill="black", font=font)
    pdf = tmp_path / "escaneado.pdf"
    img.save(pdf, resolution=150)
    res = convert(pdf, "native", {"ocr": "force"})
    assert "sigiloso" in res.markdown.lower()


def test_anonimizar_sem_internet(tmp_path):
    from markinho.anonymize import AnonOptions

    src = tmp_path / "relatorio.docx"
    shutil.copy(ROOT / "exemplos" / "relatorio.docx", src)
    res = convert(src, "auto", output=OutputOptions(anon=AnonOptions(words="Relatório")))
    assert "relatório" not in res.markdown.lower()


@pytest.mark.parametrize("fmt", ["docx", "pdf", "html", "plain", "xlsx", "csv", "chunks_jsonl", "odt", "epub"])
def test_exporta_sem_internet_nem_baixar_imagem(fmt, tmp_path):
    """Exportar não baixa nada: imagens da internet viram links (sanitize) — mesmo pelo Pandoc."""
    from markinho.exporter import FORMATS_BY_ID, export, format_backends

    if not format_backends(FORMATS_BY_ID[fmt]):
        pytest.skip(f"{fmt}: sem exportador instalado")
    md = ("# Relatório\n\nTexto com imagem remota ![rastreador](http://exemplo.invalid/pixel.png).\n\n"
          "| a | b |\n|---|---|\n| 1 | 2 |\n")
    target = tmp_path / f"saida{FORMATS_BY_ID[fmt].ext}"
    export(md, target, fmt)
    assert target.is_file() and target.stat().st_size > 0


def test_ferramentas_sem_internet(tmp_path):
    """Botão direito, lote que retoma, skill para IA e só as tabelas."""
    from PySide6.QtCore import QSettings

    from markinho import skillpack
    from markinho.__main__ import cli
    from markinho.quick import convert_here

    src = tmp_path / "relatorio.pdf"
    shutil.copy(ROOT / "exemplos" / "relatorio.pdf", src)
    s = QSettings(str(tmp_path / "m.ini"), QSettings.IniFormat)
    assert not convert_here(src, s).error
    assert cli([str(src), "-o", str(tmp_path / "lote") + "/", "--retomar"]) == 0
    assert cli([str(src), "-t", "xlsx", "-o", str(tmp_path / "t.xlsx")]) in (0, 1)
    pack = skillpack.build_skill([("Relatório", convert(src, "auto").markdown)])
    assert skillpack.to_zip(pack)


def test_o_bloqueio_funciona(sem_internet):
    """Confere o próprio teste: uma conexão de verdade é recusada e anotada."""
    import urllib.request

    with pytest.raises(OSError):
        urllib.request.urlopen("http://exemplo.invalid/", timeout=2)
    assert sem_internet
    sem_internet.clear()            # foi de propósito


def test_pp_ocr_sem_internet(tmp_path):
    """O PP-OCR usa só os modelos do computador (o RapidOCR nunca baixa nada)."""
    from markinho import ocr

    if not ocr.ppocr_ready():
        pytest.skip("modelos do PP-OCR não instalados")
    from PIL import Image, ImageDraw, ImageFont

    img = Image.new("RGB", (1240, 300), "white")
    try:
        font = ImageFont.truetype("DejaVuSans.ttf", 44)
    except OSError:
        font = ImageFont.load_default()
    ImageDraw.Draw(img).text((60, 120), "Relatório sigiloso de teste", fill="black", font=font)
    pdf = tmp_path / "escaneado_pp.pdf"
    img.save(pdf, resolution=150)
    ocr.refresh()
    res = convert(pdf, "native", {"ocr": "force", "ocr_backend": "rapidocr"})
    assert "sigiloso" in res.markdown.lower()
