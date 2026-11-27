# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 dontstopbelieve — Markinho
"""Texto alternativo de imagens gerado por IA **local** (Ollama), sem enviar nada à internet.

Requer o Ollama (https://ollama.com) rodando no computador com um modelo de visão,
por exemplo: `ollama pull qwen2.5vl:3b`, `ollama pull llava` ou `ollama pull gemma3`.
"""
from __future__ import annotations

from .i18n import tr

import base64
import json
import urllib.error
import urllib.request

VISION_HINTS = ("llava", "vl", "vision", "gemma3", "minicpm-v", "moondream", "bakllava", "llama3.2-vision",
                "granite3.2-vision", "mistral-small3", "qwen2.5vl", "qwen3-vl")
PROMPT = (tr("Descreva esta imagem em português do Brasil, em no máximo duas frases, para servir de texto "
          "alternativo em um documento. Se houver texto legível na imagem, transcreva-o. "
          "Responda só com a descrição."))


_LOCAL_HOSTS = {"localhost", "127.0.0.1", "::1"}


def _request(url: str, payload: dict | None = None, timeout: float = 5.0) -> dict:
    from urllib.parse import urlparse

    # regra do Markinho: nada sai do computador — as imagens só vão para um Ollama local
    if (urlparse(url).hostname or "").lower() not in _LOCAL_HOSTS:
        raise ValueError(tr("A descrição de imagens só usa um Ollama neste computador (localhost)."))
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"},
                                 method="POST" if data else "GET")
    # conexão local: ignora proxies configurados no sistema
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    with opener.open(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def list_models(base_url: str = "http://localhost:11434") -> list[str]:
    """Modelos instalados no Ollama (lista vazia se o Ollama não estiver rodando)."""
    try:
        data = _request(base_url.rstrip("/") + "/api/tags", timeout=2.0)
    except (urllib.error.URLError, OSError, ValueError):
        return []
    return [m.get("name", "") for m in data.get("models", []) if m.get("name")]


def vision_models(base_url: str = "http://localhost:11434") -> list[str]:
    return [m for m in list_models(base_url) if any(h in m.lower() for h in VISION_HINTS)]


def describe_image(data: bytes, model: str, base_url: str = "http://localhost:11434",
                   timeout: float = 180.0) -> str:
    payload = {"model": model, "prompt": PROMPT, "images": [base64.b64encode(data).decode()],
               "stream": False, "options": {"temperature": 0.1}}
    resp = _request(base_url.rstrip("/") + "/api/generate", payload, timeout=timeout)
    text = (resp.get("response") or "").strip().strip('"').replace("\n", " ")
    return text[:400]


def describe_all(files: dict[str, bytes], model: str, base_url: str, limit: int = 50) -> tuple[dict[str, str], list[str]]:
    """Descreve até `limit` imagens. Devolve ({caminho: descrição}, [erros])."""
    alts, errors = {}, []
    for k, (name, blob) in enumerate(files.items()):
        if k >= limit:
            errors.append(tr('Limite de {0} imagens atingido; as demais ficaram sem descrição.').format(limit))
            break
        try:
            alts[name] = describe_image(blob, model, base_url)
        except Exception as exc:  # noqa: BLE001
            errors.append(f"{name}: {exc}")
            if isinstance(exc, (urllib.error.URLError, ConnectionError)):
                break
    return alts, errors
