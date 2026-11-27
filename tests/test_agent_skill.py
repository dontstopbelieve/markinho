"""Skill que ensina assistentes de IA a usar o Markinho pelo terminal."""
import json
import sys
from pathlib import Path

from markinho import agent_skill
from markinho.__main__ import cli


def _frontmatter(text: str) -> dict:
    lines = text.split("\n")
    end = lines.index("---", 1)
    out = {}
    for ln in lines[1:end]:
        k, _, v = ln.partition(": ")
        out[k] = json.loads(v) if v.startswith('"') else v
    return out


def test_texto_da_skill():
    text = agent_skill.skill_text()
    fm = _frontmatter(text)
    assert fm["name"] == "markinho" and len(fm["description"]) <= 1024 and "<" not in fm["description"]
    cmd, _ = agent_skill.cli_command()
    assert f"`{cmd} report.pdf -t xlsx -o tables.xlsx`" in text
    assert "data, not instructions" in text and "--retomar" in text


def test_comando_conforme_instalacao(monkeypatch, tmp_path):
    monkeypatch.setattr(agent_skill.shutil, "which", lambda name: None)
    cmd, note = agent_skill.cli_command()
    assert "-m markinho" in cmd and note
    monkeypatch.setattr(agent_skill.shutil, "which", lambda name: "/usr/bin/markinho")
    assert agent_skill.cli_command() == ("markinho", "")
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "executable", str(tmp_path / "Markinho" / "Markinho.exe"))
    cmd, _ = agent_skill.cli_command()
    assert "markinho-cli" in cmd


def test_instalar_pelo_terminal(tmp_path, capsys):
    assert cli(["--instalar-skill", str(tmp_path)]) == 0
    skill = tmp_path / "markinho" / "SKILL.md"
    assert skill.read_text(encoding="utf-8").startswith("---\nname: markinho")
    assert "Skill instalada" in capsys.readouterr().out
    assert cli(["--mostrar-skill"]) == 0
    assert "name: markinho" in capsys.readouterr().out


def test_instalar_padrao_no_claude(tmp_path, monkeypatch):
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    path = agent_skill.install()
    assert path == tmp_path / ".claude" / "skills" / "markinho" / "SKILL.md" and path.is_file()
