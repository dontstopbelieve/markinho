import io
import time
from pathlib import Path

from markinho.anonymize import (AnonOptions, anonymize, mask, strip_frontmatter_private, strip_image_metadata,
                                valid_cnpj, valid_cpf, valid_pis, valid_titulo)

TEXT = """Autor: JOÃO DA SILVA, CPF 529.982.247-25, CNPJ 11.222.333/0001-81, joao.silva@exemplo.com.br.
Tel. (11) 98765-4321; CEP 01310-100. Processo 0001234-56.2024.8.26.0100.
Advogada Maria Souza OAB/SP 123.456. RG 12.345.678-9.
Assinado eletronicamente por: CARLOS PEREIRA, em 10/10/2024.
O João da Silva assinou. ![foto](contrato_assets/imagem_001.png)
"""


def test_check_digits():
    assert valid_cpf("529.982.247-25") and not valid_cpf("529.982.247-26") and not valid_cpf("111.111.111-11")
    assert valid_cnpj("11.222.333/0001-81") and not valid_cnpj("11.222.333/0001-82")
    assert valid_cnpj("12.ABC.345/01DE-35")            # CNPJ alfanumérico (exemplo da Receita)
    assert valid_pis("120.56849.90-0") and not valid_pis("120.56849.90-1")
    assert valid_titulo("1023 8501 0671") and not valid_titulo("1023 8501 0672")


def test_pseudonyms_are_consistent_and_links_kept():
    out, rep = anonymize(TEXT, AnonOptions())
    for secret in ("529.982.247-25", "11.222.333/0001-81", "joao.silva", "98765-4321", "01310-100",
                   "0001234-56.2024", "123.456", "12.345.678", "CARLOS", "Maria Souza", "JOÃO", "João"):
        assert secret not in out, secret
    assert out.count("[PESSOA 1]") == 2                 # o mesmo nome recebe o mesmo número
    assert "![foto](contrato_assets/imagem_001.png)" in out
    assert rep.counts["cpf"] == 1 and rep.total >= 10


def test_numbers_that_are_not_documents_stay():
    text = "Período 2020-2024, nota 1234-5678, CPF falso 123.456.789-00, total 12345678901, versão 1.2.3.4"
    out, rep = anonymize(text, AnonOptions(kinds=["cpf", "pis", "telefone", "cartao", "titulo"]))
    assert out == text and rep.total == 0


def test_modes_and_word_list():
    out, _ = anonymize("Contrato com a Acme Ltda em São Paulo.", AnonOptions(
        mode="marcador", words="acme ltda\nsao paulo = [CIDADE]"))
    assert out == "Contrato com a [NOME] em [CIDADE]."
    assert mask("cpf", "529.982.247-25") == "***.982.247-**"
    assert mask("email", "joao@x.com") == "j***@x.com"
    assert mask("nomes", "João da Silva") == "J. S."


def test_frontmatter_private_fields_removed():
    md = '---\ntitle: "Ata"\nauthor: "Fulano"\nkeywords:\n  - "x"\nsource: "ata fulano.docx"\npages: 2\n---\n\ntexto'
    out = strip_frontmatter_private(md)
    assert "Fulano" not in out and "source" not in out and "keywords" not in out and "pages: 2" in out


def test_convert_with_anon_hides_metadata(tmp_path):
    import docx

    from markinho.core import convert
    from markinho.postprocess import OutputOptions

    d = docx.Document()
    d.core_properties.author = "Fulana de Tal"
    d.add_paragraph("Paciente Ana Beatriz Costa, CPF 529.982.247-25.")
    src = tmp_path / "prontuario ana costa.docx"
    d.save(src)
    res = convert(src, "native", output=OutputOptions(frontmatter=True, anon=AnonOptions()))
    md = res.markdown
    assert "Fulana" not in md and "ana costa" not in md.lower() and "Ana Beatriz" not in md and "529.982" not in md
    assert "documento.docx" in md and res.anon_report.total == 2


def test_image_metadata_stripped_without_reencoding():
    from PIL import Image

    img = Image.new("RGB", (8, 8), "red")
    exif = Image.Exif()
    exif[0x010F] = "CameraSecreta"
    buf = io.BytesIO()
    img.save(buf, "JPEG", exif=exif.tobytes())
    data = buf.getvalue()
    clean = strip_image_metadata(data)
    assert b"CameraSecreta" in data and b"CameraSecreta" not in clean
    assert Image.open(io.BytesIO(clean)).size == (8, 8)
    png = io.BytesIO()
    from PIL import PngImagePlugin

    info = PngImagePlugin.PngInfo()
    info.add_text("Author", "Fulano")
    img.save(png, "PNG", pnginfo=info)
    assert b"Fulano" not in strip_image_metadata(png.getvalue())


def test_prepared_text_does_not_hang():
    evil = ("a" * 50000 + "\n") + ("1" * 50000) + (" Sr. " + "Aa " * 3000) + ("x." * 20000) + "@" * 1000
    t = time.perf_counter()
    anonymize(evil, AnonOptions(kinds=[k for k, *_ in __import__("markinho.anonymize").anonymize.KINDS]))
    assert time.perf_counter() - t < 5


def test_saved_settings_reach_quick_mode(tmp_path):
    from PySide6.QtCore import QSettings

    from markinho.quick import anon_options, save_anon_options, saved_job

    s = QSettings(str(tmp_path / "s.ini"), QSettings.IniFormat)
    save_anon_options(s, AnonOptions(kinds=["email"], mode="marcador", words="Fulano"))
    s.setValue("anon/enabled", True)
    o = anon_options(s)
    assert o.kinds == ["email"] and o.mode == "marcador" and o.words == "Fulano"
    assert saved_job(s, Path("x.docx"))[3].anon.kinds == ["email"]


def test_list_ignores_case_and_accents_but_needs_each_variation():
    out, _ = anonymize("JOAO DA SILVA e joão da silva; depois só João.", AnonOptions(kinds=[], words="João da Silva"))
    assert out.count("[NOME 1]") == 2 and "João." in out


def test_disclaimer_is_documented():
    from markinho.anonymize import DISCLAIMER
    from markinho.privacy import TEXT

    assert "não se responsabiliza" in DISCLAIMER and "não se responsabiliza" in " ".join(TEXT.split())
    rtf = (Path(__file__).resolve().parents[1] / "packaging" / "windows" / "termos.rtf").read_text("ascii")
    assert "responsabiliza" in rtf
