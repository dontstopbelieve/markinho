# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 dontstopbelieve — Markinho
"""Instância única: o Windows abre o programa uma vez para cada arquivo selecionado no botão
direito. Em vez de abrir 10 janelas, a primeira instância recebe os arquivos das outras.

Usa um canal local (QLocalServer: "named pipe" no Windows, socket no Linux/macOS), que só aceita
conexões do próprio computador e do mesmo usuário — nada passa pela rede.
"""
from __future__ import annotations

import getpass
import json
import logging
import os
import re
import time
from typing import Callable

from PySide6.QtCore import QObject
from PySide6.QtNetwork import QLocalServer, QLocalSocket


MAX_MESSAGE = 4 * 1024 * 1024        # 4 MB: dá para milhares de caminhos de arquivo


def channel_name(kind: str) -> str:
    """Nome do canal por usuário (dois usuários no mesmo computador não se misturam)."""
    try:
        user = getpass.getuser()
    except Exception:  # noqa: BLE001
        user = "usuario"
    return "markinho-" + kind + "-" + re.sub(r"[^A-Za-z0-9_.-]", "_", user)


def forward(name: str, paths: list[str], timeout_ms: int = 1500) -> bool:
    """Envia `paths` para a instância que já está aberta. True = entregue (esta pode fechar)."""
    sock = QLocalSocket()
    sock.connectToServer(name)
    if not sock.waitForConnected(timeout_ms):
        return False
    sock.write((json.dumps({"paths": paths}) + "\n").encode("utf-8"))
    ok = sock.waitForBytesWritten(timeout_ms)
    sock.disconnectFromServer()
    if sock.state() != QLocalSocket.UnconnectedState:
        sock.waitForDisconnected(timeout_ms)
    return ok


class Listener(QObject):
    """Recebe os arquivos enviados por outras instâncias e chama `on_paths(lista)`."""

    def __init__(self, name: str, on_paths: Callable[[list[str]], None]):
        super().__init__()
        self.name, self.on_paths = name, on_paths
        self.server = QLocalServer(self)
        self.server.setSocketOptions(QLocalServer.UserAccessOption)
        self.server.newConnection.connect(self._accept)

    def listen(self) -> bool:
        if self.server.listen(self.name):
            return True
        # canal "esquecido" por uma instância que fechou sem limpar (Linux/macOS)
        QLocalServer.removeServer(self.name)
        return self.server.listen(self.name)

    def _accept(self) -> None:
        """Lê cada conexão inteira na hora e a encerra (sem deixar conexões pendentes: uma conexão
        “pendurada” derrubava o programa quando o Markinho fechava)."""
        while self.server.hasPendingConnections():
            sock = self.server.nextPendingConnection()
            buf = bytearray()
            deadline = time.monotonic() + 1.0
            while b"\n" not in buf and len(buf) <= MAX_MESSAGE and time.monotonic() < deadline:
                if sock.bytesAvailable() or sock.waitForReadyRead(200):
                    buf.extend(bytes(sock.readAll()))
                elif sock.state() != QLocalSocket.ConnectedState:
                    buf.extend(bytes(sock.readAll()))
                    break
            sock.abort()
            sock.deleteLater()
            line = bytes(buf).split(b"\n", 1)[0]
            if not line or len(buf) > MAX_MESSAGE:
                continue
            try:
                paths = json.loads(line.decode("utf-8")).get("paths", [])
            except (ValueError, AttributeError):
                continue
            if isinstance(paths, list):
                self.on_paths([str(p) for p in paths])

def claim(kind: str, paths: list[str], on_paths: Callable[[list[str]], None]) -> Listener | None:
    """Torna esta a instância principal (devolve o Listener) ou entrega `paths` à que já existe
    (devolve None: esta instância deve fechar).

    Várias instâncias abertas ao mesmo tempo (seleção múltipla) disputam o canal: quem não
    consegue escutar tenta entregar de novo por alguns instantes."""
    name = channel_name(kind)
    log = logging.getLogger("markinho.single")
    if os.environ.get("MARKINHO_DEBUG") == "1" and not logging.getLogger().handlers:
        logging.basicConfig(level=logging.DEBUG, format="%(name)s: %(message)s")
    for attempt in range(6):
        if forward(name, paths, 400 if attempt else 800):
            log.debug("pid %s: %d arquivo(s) entregue(s) à instância aberta", os.getpid(), len(paths))
            return None
        listener = Listener(name, on_paths)
        if listener.server.listen(name):
            log.debug("pid %s: instância principal (%s)", os.getpid(), name)
            return listener
        time.sleep(0.15)
    listener = Listener(name, on_paths)
    listener.listen()       # se nem assim conseguir, segue sozinha (sem receber de outras)
    return listener
