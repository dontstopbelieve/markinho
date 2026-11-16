# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 dontstopbelieve — Markinho
"""Pasta monitorada: todo arquivo novo que aparecer na pasta é convertido sozinho (enquanto o
Markinho estiver aberto), com as configurações salvas, e o .md vai para a pasta de saída."""
from __future__ import annotations

import os
from pathlib import Path

from PySide6.QtCore import QFileSystemWatcher, QObject, QRunnable, QThreadPool, QTimer, Signal

IGNORE_EXT = {".md", ".markdown", ".tmp", ".part", ".crdownload", ".partial", ".download"}


def candidates(folder: Path) -> dict[str, tuple[int, float]]:
    """{caminho: (tamanho, data)} dos arquivos convertíveis da pasta (sem subpastas)."""
    from .engines import all_input_extensions

    exts = set(all_input_extensions())
    out = {}
    try:
        with os.scandir(folder) as it:
            for e in it:
                name = e.name
                if not e.is_file() or name.startswith((".", "~$")):
                    continue
                ext = os.path.splitext(name)[1].lower()
                if ext in IGNORE_EXT or ext not in exts:
                    continue
                st = e.stat()
                out[e.path] = (st.st_size, st.st_mtime)
    except OSError:
        pass
    return out


class _Job(QRunnable):
    def __init__(self, watcher: "FolderWatcher", path: str):
        from .quick import SettingsSnapshot

        super().__init__()
        self.w, self.path = watcher, path
        self.snapshot = SettingsSnapshot()      # lida na thread da interface, antes de começar

    def run(self) -> None:
        from .quick import convert_here

        self.w._result.emit(convert_here(self.path, self.snapshot, 0, self.w.out_dir))


class FolderWatcher(QObject):
    converted = Signal(object)          # quick.QuickResult
    _result = Signal(object)

    def __init__(self, folder: str | Path, out_dir: str | Path | None = None, parent=None):
        super().__init__(parent)
        self.folder = Path(folder)
        self.out_dir = Path(out_dir) if out_dir else None
        self._known: dict[str, tuple[int, float]] = {}
        self._pending: dict[str, tuple[int, float]] = {}
        self._fs = QFileSystemWatcher(self)
        self._fs.directoryChanged.connect(lambda _p: self._debounce.start())
        self._debounce = QTimer(self, singleShot=True, interval=1500, timeout=self.scan)
        self._poll = QTimer(self, interval=5000, timeout=self.scan)    # pastas de rede nem sempre avisam
        self._pool = QThreadPool(self)
        self._pool.setMaxThreadCount(1)
        self._result.connect(self.converted.emit)

    def start(self) -> bool:
        if not self.folder.is_dir():
            return False
        self._known = candidates(self.folder)     # arquivos que já estavam lá não são convertidos
        self._fs.addPath(str(self.folder))
        self._poll.start()
        return True

    def stop(self) -> None:
        self._poll.stop()
        self._debounce.stop()
        if self._fs.directories():
            self._fs.removePaths(self._fs.directories())

    def scan(self) -> None:
        now = candidates(self.folder)
        for path, sig in now.items():
            if self._known.get(path) == sig:
                continue
            if self._pending.get(path) == sig:     # tamanho parou de mudar: terminou de copiar/baixar
                self._pending.pop(path)
                self._known[path] = sig
                self._pool.start(_Job(self, path))
            else:
                self._pending[path] = sig
        for gone in set(self._known) - set(now):
            self._known.pop(gone, None)
        if self._pending:
            self._debounce.start()
