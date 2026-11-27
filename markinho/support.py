# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 dontstopbelieve — Markinho
"""Apoie o Markinho: dados do Pix e o agradecimento único em marcos de uso.

O agradecimento aparece no máximo uma vez em cada marco (100 e 1.000 documentos convertidos na janela
principal), nunca no botão direito, na pasta monitorada ou durante uma conversão, e some para sempre se a
pessoa escolher “Não mostrar de novo”. A contagem fica só nas configurações do computador.
"""
from __future__ import annotations

PIX_KEY = "1487d3bd-979f-482e-a83a-026329e0b143"
# BR Code (padrão do Banco Central) — nome no código: MARKINHO; o app do banco mostra o nome do recebedor
PIX_PAYLOAD = "00020126580014br.gov.bcb.pix01361487d3bd-979f-482e-a83a-026329e0b1435204000053039865802BR5908MARKINHO6006BRASIL62070503***63047522"
MILESTONES = (100, 1000)


def pix_crc_ok(payload: str = PIX_PAYLOAD) -> bool:
    """Confere o código de checagem (CRC16-CCITT) do Pix copia e cola."""
    body, crc = payload[:-4], payload[-4:]
    value = 0xFFFF
    for b in body.encode():
        value ^= b << 8
        for _ in range(8):
            value = ((value << 1) ^ 0x1021) if value & 0x8000 else (value << 1)
            value &= 0xFFFF
    return f"{value:04X}" == crc


def count_conversion(settings) -> int | None:
    """Soma uma conversão concluída. Devolve o marco atingido agora (100, 1000) ou None."""
    n = int(settings.value("stats/converted", 0) or 0) + 1
    settings.setValue("stats/converted", n)
    if settings.value("support/never", False, type=bool):
        return None
    for m in MILESTONES:
        if n >= m and not settings.value(f"support/shown_{m}", False, type=bool):
            settings.setValue(f"support/shown_{m}", True)
            return m
    return None
