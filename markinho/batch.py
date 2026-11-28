# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 dontstopbelieve — Markinho
"""Lotes que retomam de onde pararam: terminal (``--retomar``), botão direito, pasta monitorada e janela.

Privacidade: o registro guarda só impressões digitais (do caminho e do conteúdo), o nome do arquivo gerado e
a situação — nunca o nome ou o caminho do arquivo original nem o texto dos erros.

Na pasta de saída fica um registro (``.markinho-lote.json``) com a “impressão digital” (SHA-256) de cada
arquivo de origem, a configuração usada e o arquivo gerado. Se o lote cair no meio (queda de energia,
computador desligado, erro), rodar de novo pula o que já está pronto e não mudou, e refaz só o que faltou,
o que deu erro e o que mudou (arquivo ou configuração). O registro é gravado a cada arquivo, e os arquivos
são gravados de forma atômica (primeiro num temporário, depois trocados), então nunca fica meio arquivo.
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
import tempfile
from pathlib import Path

MANIFEST = ".markinho-lote.json"
_VERSION = 1


def file_hash(path: Path | str, chunk: int = 1 << 20) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while block := f.read(chunk):
            h.update(block)
    return h.hexdigest()


def config_key(settings: dict) -> str:
    """Resumo da configuração: mudar motor, opções, imagens, perfil… faz o arquivo ser convertido de novo."""
    raw = json.dumps(settings, sort_keys=True, ensure_ascii=False, default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def job_key(engine: str, opts: dict, fix, output, extra: dict | None = None) -> str:
    """Configuração de uma conversão (motor, opções, correção, saída) para o registro do lote."""
    from dataclasses import asdict, is_dataclass

    def plain(x):
        return asdict(x) if is_dataclass(x) and not isinstance(x, type) else x

    return config_key({"engine": engine, "opts": opts, "fix": plain(fix), "output": plain(output), **(extra or {})})


def enabled(settings) -> bool:
    """Opção “Retomar lotes interrompidos” (Configurações > Desempenho), ligada por padrão."""
    try:
        return bool(settings.value("batch/resume", True, type=bool))
    except Exception:  # noqa: BLE001
        return True


def atomic_write(path: Path, data: bytes | str) -> None:
    """Grava num temporário na mesma pasta e troca no fim: um arquivo pela metade nunca fica no lugar."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=".~", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(data.encode("utf-8") if isinstance(data, str) else data)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise


def _stamp(src: Path | str) -> dict:
    try:
        st = os.stat(src)
        return {"size": st.st_size, "mtime": int(st.st_mtime)}
    except OSError:
        return {"size": None, "mtime": None}


def _safe_name(name: object) -> str | None:
    """Nome guardado no registro só vale se for um nome de arquivo simples (o registro pode ter sido mexido)."""
    if not isinstance(name, str) or not name or name in (".", "..") or "/" in name or "\\" in name \
            or "\x00" in name or name.startswith(".") or ":" in name:
        return None
    return name


class Manifest:
    """Registro do lote na pasta de saída."""

    def __init__(self, folder: Path):
        self.folder = Path(folder)
        self.path = self.folder / MANIFEST
        self.entries: dict[str, dict] = {}
        self.corrupt = False
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            if isinstance(data, dict) and isinstance(data.get("files"), dict):
                self.entries = {k: v for k, v in data["files"].items() if isinstance(k, str) and isinstance(v, dict)}
        except FileNotFoundError:
            pass
        except (OSError, ValueError):
            self.corrupt = True                    # registro estragado: recomeça (nada é apagado)

    @staticmethod
    def key(src: Path | str) -> str:
        """Impressão digital do caminho de origem, não o caminho: o registro fica na pasta de saída, que pode
        ser compartilhada (inclusive depois de anonimizar), e o nome do arquivo original não pode ir junto."""
        return hashlib.sha256(str(Path(src).resolve()).encode("utf-8", "surrogatepass")).hexdigest()[:32]

    def output_name(self, src: Path | str, cfg: str) -> str | None:
        """Nome já reservado para este arquivo nesta configuração (para gravar por cima ao retomar)."""
        e = self.entries.get(self.key(src))
        return _safe_name(e.get("output")) if e and e.get("config") == cfg else None

    def is_done(self, src: Path | str, sha: str, cfg: str) -> bool:
        e = self.entries.get(self.key(src))
        name = _safe_name(e.get("output")) if e else None
        return bool(e and name and e.get("status") == "ok" and e.get("sha256") == sha and e.get("config") == cfg
                    and (self.folder / name).is_file())

    def start(self, src: Path | str, sha: str, cfg: str, output: str) -> None:
        self.entries[self.key(src)] = {"sha256": sha, "config": cfg, "output": output, "status": "convertendo",
                                       **_stamp(src)}
        self.save()

    def seen(self, src: Path | str) -> bool:
        """Já foi convertido (ou ignorado de propósito) e o arquivo não mudou de tamanho nem de data?
        Rápido: não calcula a impressão digital (usado pela pasta monitorada a cada abertura)."""
        e = self.entries.get(self.key(src))
        return bool(e and e.get("status") in ("ok", "ignorado") and _stamp(src) == {
            "size": e.get("size"), "mtime": e.get("mtime")})

    def ignore(self, paths) -> None:
        """Marca arquivos que já estavam na pasta quando a monitoração começou (não serão convertidos)."""
        for src in paths:
            self.entries.setdefault(self.key(src), {"status": "ignorado", **_stamp(src)})
        self.save()

    def fail(self, src: Path | str, sha: str, cfg: str, error: str) -> None:
        """Erro antes de saber o nome de saída (a conversão falhou): fica registrado para refazer depois."""
        e = self.entries.get(self.key(src)) or {}
        self.entries[self.key(src)] = {**e, "sha256": sha, "config": cfg, "status": "erro", **_stamp(src)}
        self.save()                    # o texto do erro não é guardado (pode conter nomes de arquivo)

    def finish(self, src: Path | str, ok: bool, error: str = "") -> None:
        e = self.entries.setdefault(self.key(src), {})
        e["status"] = "ok" if ok else "erro"
        e.update(_stamp(src))
        self.save()

    def save(self) -> None:
        atomic_write(self.path, json.dumps({"markinho": _VERSION, "files": self.entries}, ensure_ascii=False, indent=1))
        hide_file(self.path)


def hide_file(path: Path) -> None:
    """No Windows, marca o arquivo como oculto (no Linux e no Mac o ponto no começo do nome já esconde): o
    registro do lote não aparece como “um arquivo a mais” na pasta de saída."""
    if sys.platform != "win32":
        return
    try:
        import ctypes

        FILE_ATTRIBUTE_HIDDEN = 0x2
        ctypes.windll.kernel32.SetFileAttributesW(str(path), FILE_ATTRIBUTE_HIDDEN)
    except Exception:  # noqa: BLE001 — se não der para esconder, o arquivo continua funcionando
        pass
