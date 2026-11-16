"""Servidor MCP local: ferramentas, pastas autorizadas e permissão de gravação."""
import asyncio
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

pytest.importorskip("mcp")
from mcp.client import Client  # noqa: E402

from markinho import mcp_server  # noqa: E402

FX = Path(__file__).parent / "fixtures"
ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture
def setup(tmp_path, monkeypatch):
    allowed = tmp_path / "permitida"
    allowed.mkdir()
    (tmp_path / "secreta").mkdir()
    shutil.copy(ROOT / "exemplos" / "relatorio.docx", allowed / "relatorio.docx")
    shutil.copy(FX / "antigo.doc", allowed / "antigo.doc")
    (tmp_path / "secreta" / "senhas.txt").write_text("segredo")
    monkeypatch.setattr(mcp_server, "config_path", lambda: tmp_path / "mcp.json")
    monkeypatch.delenv("MARKINHO_MCP_FOLDERS", raising=False)
    monkeypatch.delenv("MARKINHO_MCP_ALLOW_WRITE", raising=False)
    mcp_server.save_config([str(allowed)], allow_write=False)
    return tmp_path, allowed


def call(tool, args):
    async def go():
        async with Client(mcp_server.build_server()) as c:
            return await c.call_tool(tool, args)
    return asyncio.run(go())


def text_of(res):
    return "".join(getattr(c, "text", "") for c in res.content)


def test_tools_listed():
    async def go():
        async with Client(mcp_server.build_server()) as c:
            return [t.name for t in (await c.list_tools()).tools]
    names = asyncio.run(go())
    assert {"markinho_info", "list_documents", "convert_document", "convert_to_chunks", "export_markdown",
            "save_markdown"} <= set(names)


def test_convert_and_list(setup):
    tmp, allowed = setup
    res = call("convert_document", {"path": str(allowed / "relatorio.docx")})
    assert not res.is_error and "# Relatório Trimestral" in text_of(res)
    res = call("convert_document", {"path": "antigo.doc", "profile": "llm"})     # relativo à pasta autorizada
    assert not res.is_error and "Relatório Antigo" in text_of(res)
    listing = call("list_documents", {}).structured_content
    names = {Path(f["path"]).name for f in listing["files"]}
    assert names == {"relatorio.docx", "antigo.doc"}


def test_chunks(setup):
    _, allowed = setup
    data = call("convert_to_chunks", {"path": str(allowed / "relatorio.docx"), "chunk_size": 400}).structured_content
    assert data["total"] >= 1 and data["chunks"][0]["source"] == "relatorio.docx"


@pytest.mark.parametrize("bad", ["../secreta/senhas.txt", "SECRET_ABS", "/etc/passwd"])
def test_access_outside_denied(setup, bad):
    tmp, allowed = setup
    path = str(tmp / "secreta" / "senhas.txt") if bad == "SECRET_ABS" else bad
    res = call("convert_document", {"path": path})
    assert res.is_error and "negado" in text_of(res).lower()


def test_symlink_escape_denied(setup):
    tmp, allowed = setup
    link = allowed / "atalho.txt"
    try:
        link.symlink_to(tmp / "secreta" / "senhas.txt")
    except OSError:
        pytest.skip("sem suporte a links simbólicos")
    res = call("convert_document", {"path": str(link)})
    assert res.is_error and "negado" in text_of(res).lower()


def test_no_folders_configured(setup):
    tmp, _ = setup
    mcp_server.save_config([], allow_write=False)
    res = call("convert_document", {"path": str(tmp / "permitida" / "relatorio.docx")})
    assert res.is_error and "nenhuma pasta autorizada" in text_of(res).lower()


def test_write_requires_permission(setup):
    _, allowed = setup
    args = {"markdown": "# Olá\n\nTexto.", "output_path": str(allowed / "saida.docx"), "format": "docx"}
    res = call("export_markdown", args)
    assert res.is_error and "não está permitido" in text_of(res)
    mcp_server.save_config([str(allowed)], allow_write=True)
    res = call("export_markdown", args)
    assert not res.is_error and (allowed / "saida.docx").is_file()
    res = call("export_markdown", args)                                    # não sobrescreve sem pedir
    assert res.is_error and "já existe" in text_of(res)
    res = call("save_markdown", {"path": str(allowed / "antigo.doc")})
    assert not res.is_error and (allowed / "antigo.md").is_file() and (allowed / "antigo_assets").is_dir()


def test_install_claude_desktop_keeps_other_servers(tmp_path):
    cfg = tmp_path / "claude_desktop_config.json"
    cfg.write_text(json.dumps({"mcpServers": {"outro": {"command": "x"}}, "tema": "escuro"}))
    mcp_server.install_claude_desktop(cfg)
    data = json.loads(cfg.read_text())
    assert data["mcpServers"]["outro"] == {"command": "x"} and data["tema"] == "escuro"
    assert data["mcpServers"]["markinho"]["args"][-1] == "--mcp"
    assert (tmp_path / "claude_desktop_config.json.bak").is_file()


def test_stdio_subprocess(setup, tmp_path):
    """O servidor real, iniciado como o Claude Desktop faria (subprocesso via stdio)."""
    from mcp import StdioServerParameters

    _, allowed = setup
    params = StdioServerParameters(command=sys.executable, args=["-m", "markinho", "--mcp"], cwd=str(ROOT),
                                   env={"MARKINHO_MCP_FOLDERS": str(allowed), "PYTHONPATH": str(ROOT),
                                        "QT_QPA_PLATFORM": "offscreen", "HOME": str(tmp_path),
                                        "PATH": "/usr/bin:/bin"})

    async def go():
        async with Client(params) as c:
            return await c.call_tool("convert_document", {"path": str(allowed / "relatorio.docx")})
    res = asyncio.run(go())
    assert not res.is_error and "Relatório Trimestral" in text_of(res)


def test_save_markdown_name_template(setup):
    _, allowed = setup
    mcp_server.save_config([str(allowed)], allow_write=True)
    res = call("save_markdown", {"path": str(allowed / "antigo.doc"), "name_template": "Arquivo {nome}",
                                 "safe_names": True})
    assert not res.is_error, text_of(res)
    assert (allowed / "arquivo-antigo.md").is_file() and (allowed / "arquivo-antigo_assets").is_dir()
    res = call("save_markdown", {"path": str(allowed / "antigo.doc"), "name_template": "{x}"})
    assert res.is_error and "desconhecido" in text_of(res)


def test_list_pattern_cannot_leave_folder(setup):
    tmp, allowed = setup
    res = call("list_documents", {"pattern": "../secreta/*"})
    assert res.is_error and "filtro" in text_of(res)
    (allowed / "atalho.txt").symlink_to(tmp / "secreta" / "senhas.txt")
    listed = json.loads(text_of(call("list_documents", {"pattern": "*.txt"})))
    assert all("atalho" not in f["path"] for f in listed["files"])


def test_export_does_not_embed_files_outside_or_download(setup):
    tmp, allowed = setup
    mcp_server.save_config([str(allowed)], allow_write=True)
    from PIL import Image

    Image.new("RGB", (8, 8), "red").save(tmp / "secreta" / "foto.png")
    Image.new("RGB", (8, 8), "blue").save(allowed / "ok.png")
    md = (f"# Teste\n\n![segredo]({tmp / 'secreta' / 'foto.png'})\n\n![ok](ok.png)\n\n"
          "![rede](http://exemplo.invalid/x.png)\n\n<script>alert(1)</script>\n")
    res = call("export_markdown", {"markdown": md, "output_path": str(allowed / "saida.html"), "format": "html"})
    assert not res.is_error, text_of(res)
    html = (allowed / "saida.html").read_text(encoding="utf-8")
    assert "<script>alert" not in html
    assert "foto.png" not in html                      # imagem de fora das pastas: removida
    assert 'href="http://exemplo.invalid/x.png"' in html and 'src="http://exemplo.invalid' not in html
