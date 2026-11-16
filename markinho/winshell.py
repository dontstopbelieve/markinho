# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 dontstopbelieve — Markinho
"""Menu “Markinho” no botão direito do Windows, ligado e desligado pelo próprio programa.

O instalador (.exe) já cria o menu; a versão ZIP portátil não instala nada, por isso esta opção
existe também dentro do Markinho (Ferramentas > Botão direito do Windows). Grava só para o usuário
atual (HKEY_CURRENT_USER), sem pedir senha de administrador — as mesmas entradas do instalador.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

DOC_EXTS = ["pdf", "docx", "doc", "odt", "rtf", "xlsx", "xlsm", "xls", "ods", "csv", "pptx", "ppt", "odp",
            "epub", "html", "htm", "txt", "png", "jpg", "jpeg", "tif", "tiff", "bmp", "webp"]
MD_EXTS = ["md", "markdown"]
BASE = r"Software\Classes\SystemFileAssociations\.{ext}\shell\Markinho"


def available() -> bool:
    """Só no Windows e no programa empacotado (instalador ou ZIP), que tem o Markinho.exe."""
    return os.name == "nt" and getattr(sys, "frozen", False)


def exe_path() -> str:
    return str(Path(sys.executable).resolve())


def entries(exe: str) -> list[tuple[str, str, str]]:
    """[(subchave, nome do valor, dado)] — o mesmo menu que o instalador cria."""
    out: list[tuple[str, str, str]] = []

    def menu(ext: str, items: list[tuple[str, str, str]]) -> None:
        base = BASE.format(ext=ext)
        out.extend([(base, "MUIVerb", "Markinho"), (base, "SubCommands", ""), (base, "Icon", exe)])
        for sub, label, flag in items:
            key = base + "\\shell\\" + sub
            cmd = f'"{exe}" {flag + " " if flag else ""}"%1"'
            out.extend([(key, "", label), (key, "MultiSelectModel", "Player"), (key + "\\command", "", cmd)])

    for ext in DOC_EXTS:
        menu(ext, [("1perguntar", "Converter para Markdown…", "--converter-para-md"),
                   ("2aqui", "Converter para Markdown aqui", "--converter-aqui"),
                   ("3abrir", "Abrir no Markinho", "")])
    for ext in MD_EXTS:
        menu(ext, [("1exportar", "Converter Markdown para… (Word, PDF, HTML…)", "--exportar"),
                   ("2abrir", "Abrir no Markinho", "")])
    return out


class _WinReg:
    """Acesso ao registro do usuário (HKEY_CURRENT_USER)."""

    def __init__(self):
        import winreg

        self.w = winreg

    def set(self, key: str, name: str, value: str) -> None:
        with self.w.CreateKeyEx(self.w.HKEY_CURRENT_USER, key, 0, self.w.KEY_WRITE) as k:
            self.w.SetValueEx(k, name, 0, self.w.REG_SZ, value)

    def get(self, key: str, name: str) -> str | None:
        try:
            with self.w.OpenKey(self.w.HKEY_CURRENT_USER, key) as k:
                return self.w.QueryValueEx(k, name)[0]
        except OSError:
            return None

    def delete_tree(self, key: str) -> None:
        try:
            with self.w.OpenKey(self.w.HKEY_CURRENT_USER, key, 0, self.w.KEY_READ | self.w.KEY_WRITE) as k:
                while True:
                    try:
                        sub = self.w.EnumKey(k, 0)
                    except OSError:
                        break
                    self.delete_tree(key + "\\" + sub)
            self.w.DeleteKey(self.w.HKEY_CURRENT_USER, key)
        except OSError:
            pass


def _notify() -> None:
    """Avisa o Explorador do Windows para recarregar os menus."""
    try:
        import ctypes

        ctypes.windll.shell32.SHChangeNotify(0x08000000, 0, None, None)
    except Exception:  # noqa: BLE001
        pass


def register(exe: str | None = None, reg=None) -> int:
    reg = reg or _WinReg()
    items = entries(exe or exe_path())
    for key, name, value in items:
        reg.set(key, name, value)
    _notify()
    return len(items)


def unregister(reg=None) -> None:
    reg = reg or _WinReg()
    for ext in DOC_EXTS + MD_EXTS:
        reg.delete_tree(BASE.format(ext=ext))
    _notify()


def is_registered(reg=None) -> bool:
    try:
        reg = reg or _WinReg()
    except ImportError:
        return False
    cmd = reg.get(BASE.format(ext="pdf") + r"\shell\2aqui\command", "")
    return bool(cmd)
