# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 dontstopbelieve — Markinho
"""Conversor nativo de PDF com análise de layout (sem IA).

Resolve, com heurísticas geométricas, os problemas mais comuns de PDF → Markdown:

* títulos detectados pelo tamanho/peso da fonte;
* tabelas com linhas desenhadas (pdfplumber) → tabelas Markdown;
* **várias colunas**: acha o "corredor" vertical entre colunas e lê uma de cada vez;
* **cabeçalhos/rodapés**: remove linhas repetidas nas margens e/ou corta margens fixas;
* **código**: linhas em fonte monoespaçada viram bloco ``` com a indentação preservada;
* **imagens**: recortadas da página e salvas como ativos;
* **OCR automático** nas páginas sem texto (escaneadas), com Tesseract ou RapidOCR.
"""
from __future__ import annotations

from .i18n import tr

import re
import statistics
from pathlib import Path

from .core import ConversionError, current_sink, option

_MONO_RE = re.compile(r"mono|courier|consol|menlo|code|typewriter|fixed|inconsolata|source ?code|dejavusansm", re.I)
_BOLD_RE = re.compile(r"bold|black|heavy|semibold|demi", re.I)
NO_TEXT = (tr("_Nenhum texto encontrado. O PDF provavelmente é uma imagem escaneada e não há OCR "
           "disponível — instale o Tesseract ou use o motor **Docling**/**Marker**._"))

# Espaço entre palavras proporcional ao tamanho da letra (10% da altura): PDFs gerados pelo LaTeX
# e jornais usam espaços estreitos (~1,5 pt) que a tolerância fixa padrão (3 pt) colava
# (“Despitethesubstantial…”). Testado em artigos, jornais e relatórios (27/11/2026).
WORD_GAP = {"x_tolerance_ratio": 0.10}


# --------------------------------------------------------------------------- #
# Utilidades
# --------------------------------------------------------------------------- #
def parse_pages(spec: str, total: int) -> list[int]:
    """'1-3,5' -> [0, 1, 2, 4] (índices base 0). Vazio = todas."""
    spec = (spec or "").strip()
    if not spec:
        return list(range(total))
    pages: list[int] = []
    for part in spec.replace(" ", "").split(","):
        if not part:
            continue
        try:
            if "-" in part:
                a, b = part.split("-", 1)
                pages += range(int(a or 1) - 1, min(int(b or total), total))
            else:
                pages.append(int(part) - 1)
        except ValueError as exc:
            raise ConversionError(tr("Intervalo de páginas inválido: '{0}'").format(spec)) from exc
    return [p for p in dict.fromkeys(pages) if 0 <= p < total]


def _key(text: str) -> str:
    return re.sub(r"\d+", "#", text.strip().lower())


def repeated_lines(pages_lines: list[list[str]], edge: int = 2) -> set[str]:
    """Linhas que se repetem no topo/rodapé de ≥ 60% das páginas (números ignorados)."""
    if len(pages_lines) < 3:
        return set()
    counts: dict[str, int] = {}
    for lines in pages_lines:
        seen = set()
        for ln in lines[:edge] + lines[-edge:]:
            k = _key(ln)
            if k and k not in seen:
                seen.add(k)
                counts[k] = counts.get(k, 0) + 1
    limit = max(3, int(len(pages_lines) * 0.6))
    return {k for k, n in counts.items() if n >= limit}


def _title(meta_title: str | None, path: Path) -> str:
    from .postprocess import useful_title

    return useful_title(meta_title) or path.stem


# --------------------------------------------------------------------------- #
# Palavras -> linhas ("segmentos")
# --------------------------------------------------------------------------- #
def word_gutter(words: list[dict], width: float) -> float | None:
    """Corredor vertical entre colunas achado pelas palavras (não pelas linhas): mesmo estreito (~5 pt, comum
    em enciclopédias e jornais), ele aparece porque as palavras das duas colunas nunca o atravessam, de cima a
    baixo. Devolve o x do meio do corredor, ou None se a página tem uma coluna só."""
    body = [w for w in words if w.get("upright", True) and (w["x1"] - w["x0"]) < width * 0.3]
    if len(body) < 40:
        return None
    lo, hi = int(width * 0.3), int(width * 0.7)
    cover = [0] * (hi - lo + 1)
    for w in body:
        for x in range(max(lo, int(w["x0"])), min(hi, int(w["x1"])) + 1):
            cover[x - lo] += 1
    tol = max(1, int(len(body) * 0.01))           # títulos e figuras que atravessam o corredor
    runs, start = [], None
    for i, c in enumerate(cover + [tol + 1]):
        if c <= tol and start is None:
            start = i
        elif c > tol and start is not None:
            if i - start >= 4:
                runs.append((i - start, lo + (start + i) / 2))
            start = None
    # o maior corredor com texto de verdade dos DOIS lados (a margem vazia da direita não conta)
    for _length, x in sorted(runs, reverse=True):
        left = [w for w in body if w["x1"] <= x]
        right = [w for w in body if w["x0"] >= x]
        if len(left) < len(body) * 0.25 or len(right) < len(body) * 0.25:
            continue
        if len({round(w["top"]) for w in left}) >= 8 and len({round(w["top"]) for w in right}) >= 8:
            return x
    return None


def words_to_segments(words: list[dict], split_x: float | None = None) -> list[dict]:
    """Agrupa palavras em linhas e quebra a linha onde há um vão grande (colunas). `split_x`: corredor entre
    colunas (de `word_gutter`) — a linha é quebrada ali mesmo que o vão seja estreito."""
    words = sorted(words, key=lambda w: (round(w["top"]), w["x0"]))
    rows: list[list[dict]] = []
    for w in words:
        size = w.get("size", 10) or 10
        for row in reversed(rows[-4:]):
            ref = row[0]
            if abs(w["top"] - ref["top"]) <= 0.45 * min(size, ref.get("size", size) or size) \
                    or abs(w["bottom"] - ref["bottom"]) <= 0.3 * size:
                row.append(w)
                break
        else:
            rows.append([w])
    segs = []
    for row in rows:
        row.sort(key=lambda w: w["x0"])
        cur = [row[0]]
        for w in row[1:]:
            size = statistics.median([c.get("size", 10) or 10 for c in cur])
            crosses = split_x is not None and cur[-1]["x1"] <= split_x + 1 and w["x0"] >= split_x - 1
            if crosses or w["x0"] - cur[-1]["x1"] > max(1.8 * size, 14):
                segs.append(_make_seg(cur))
                cur = [w]
            else:
                cur.append(w)
        segs.append(_make_seg(cur))
    return segs


def _make_seg(ws: list[dict]) -> dict:
    sizes = [round(w.get("size", 10) or 10, 1) for w in ws]
    fonts = [w.get("fontname", "") or "" for w in ws]
    n = len(ws)
    return {"kind": "line", "text": " ".join(w["text"] for w in ws),
            "x0": min(w["x0"] for w in ws), "x1": max(w["x1"] for w in ws),
            "top": min(w["top"] for w in ws), "bottom": max(w["bottom"] for w in ws),
            "size": statistics.median(sizes),
            "bold": sum(bool(_BOLD_RE.search(f)) for f in fonts) > n * 0.6,
            "mono": sum(bool(_MONO_RE.search(f)) for f in fonts) > n * 0.6}


# --------------------------------------------------------------------------- #
# Colunas
# --------------------------------------------------------------------------- #
def find_gutter(blocks: list[dict], width: float) -> float | None:
    """Procura um corredor vertical vazio entre 25% e 75% da largura da página."""
    narrow = [b for b in blocks if b["kind"] == "line" and (b["x1"] - b["x0"]) < width * 0.55]
    if len(narrow) < 8:
        return None
    lo, hi = int(width * 0.25), int(width * 0.75)
    cover = [0] * (hi - lo + 1)
    for b in narrow:
        for x in range(max(lo, int(b["x0"])), min(hi, int(b["x1"])) + 1):
            cover[x - lo] += 1
    # títulos centralizados e figuras atravessam o corredor: tolera alguns blocos
    tol = max(1, int(len(narrow) * 0.06))
    runs, run_start = [], None
    for i, c in enumerate(cover + [tol + 1]):
        if c <= tol and run_start is None:
            run_start = i
        elif c > tol and run_start is not None:
            if i - run_start >= 6:
                runs.append((i - run_start, lo + (run_start + i) / 2))
            run_start = None
    # o maior corredor com blocos dos dois lados (a margem vazia depois da última coluna não conta)
    for _length, best in sorted(runs, reverse=True):
        left = sum(1 for b in narrow if b["x1"] <= best)
        right = sum(1 for b in narrow if b["x0"] >= best)
        if left >= len(narrow) * 0.25 and right >= len(narrow) * 0.25:
            return best
    return None


def borderless_tables(segs: list[dict], width: float) -> tuple[list[dict], list[dict]]:
    """Tabelas SEM linhas desenhadas, achadas pelo alinhamento: 3+ linhas seguidas com 2+ células curtas cada,
    cujas colunas caem nos mesmos lugares. Devolve (blocos de tabela, segmentos que sobraram).
    Texto em colunas (linhas compridas), listas de uma coluna e sumários com pontinhos ficam de fora."""
    from .converters import md_table

    if any(sg["kind"] == "line" and _TOC_RE.match(sg["text"].strip()) for sg in segs):
        return [], segs                       # página de índice/sumário: vira lista (blocks_to_markdown)
    rows: list[list[dict]] = []
    for sg in sorted(segs, key=lambda x: (x["top"], x["x0"])):
        if rows and abs(sg["top"] - rows[-1][0]["top"]) <= 0.5 * max(sg["size"], 1):
            rows[-1].append(sg)
        else:
            rows.append([sg])

    def cell_row(r: list[dict]) -> bool:
        return (len(r) >= 2 and all(sg["kind"] == "line" and not sg.get("mono") for sg in r)
                and all(sg["x1"] - sg["x0"] < width * 0.3 for sg in r)
                and not any(re.search(r"\.{4,}|…{2,}", sg["text"]) for sg in r))      # sumário com pontinhos

    tables, used = [], set()
    i = 0
    while i < len(rows):
        if not cell_row(rows[i]):
            i += 1
            continue
        j = i + 1
        while j < len(rows) and cell_row(rows[j]) and \
                rows[j][0]["top"] - rows[j - 1][0]["bottom"] < 2.5 * max(rows[j][0]["size"], 1):
            j += 1
        group = rows[i:j]
        if len(group) >= 3:
            # colunas = faixas de x que algum segmento ocupa; os vãos que nenhum ocupa separam as colunas
            spans = sorted((sg["x0"], sg["x1"]) for r in group for sg in r)
            cols: list[list[float]] = []
            for x0, x1 in spans:
                if cols and x0 <= cols[-1][1] + 2:
                    cols[-1][1] = max(cols[-1][1], x1)
                else:
                    cols.append([x0, x1])
            if 2 <= len(cols) <= 12:
                filled = [sum(1 for r in group if any(c[0] - 1 <= (sg["x0"] + sg["x1"]) / 2 <= c[1] + 1 for sg in r))
                          for c in cols]
                # células de tabela são curtas (poucas palavras) ou números; linhas de colunas de jornal são frases
                texts = [sg["text"] for r in group for sg in r]
                words = sorted(len(t.split()) for t in texts)
                numeric = sum(1 for t in texts if re.fullmatch(r"[\d\s.,%$€£R()+\-–/:]+", t)) / max(1, len(texts))
                short = words[len(words) // 2] <= 3 or numeric >= 0.3
                # colunas de verdade aparecem na maioria das linhas (alinhamento consistente)
                if short and sum(1 for f in filled if f >= len(group) * 0.6) >= 2:
                    table_rows = []
                    for r in group:
                        cells = [""] * len(cols)
                        for sg in r:
                            mid = (sg["x0"] + sg["x1"]) / 2
                            k = min(range(len(cols)), key=lambda c: 0 if cols[c][0] <= mid <= cols[c][1]
                                    else min(abs(mid - cols[c][0]), abs(mid - cols[c][1])))
                            cells[k] = (cells[k] + " " + sg["text"]).strip()
                        table_rows.append(cells)
                    tables.append({"kind": "table", "text": md_table(table_rows), "rows": table_rows,
                                   "x0": min(sg["x0"] for r in group for sg in r),
                                   "x1": max(sg["x1"] for r in group for sg in r),
                                   "top": group[0][0]["top"], "bottom": max(sg["bottom"] for sg in group[-1])})
                    used.update(id(sg) for r in group for sg in r)
        i = j
    return tables, [sg for sg in segs if id(sg) not in used]


def reading_order(blocks: list[dict], width: float, columns: bool = True, gutter: float | None = None) -> list[dict]:
    blocks = sorted(blocks, key=lambda b: (b["top"], b["x0"]))
    if columns and gutter is None:
        gutter = find_gutter(blocks, width)
    elif not columns:
        gutter = None
    if gutter is None:
        return blocks
    out: list[dict] = []
    band: list[dict] = []

    def flush():
        left = [b for b in band if (b["x0"] + b["x1"]) / 2 < gutter]
        right = [b for b in band if (b["x0"] + b["x1"]) / 2 >= gutter]
        out.extend(sorted(left, key=lambda b: b["top"]))
        out.extend(sorted(right, key=lambda b: b["top"]))
        band.clear()

    for b in blocks:
        spans = b["x0"] < gutter - 2 and b["x1"] > gutter + 2
        if spans:                       # título/figura que ocupa a largura toda separa as faixas
            flush()
            out.append(b)
        else:
            band.append(b)
    flush()
    return out


# --------------------------------------------------------------------------- #
# Blocos -> Markdown
# --------------------------------------------------------------------------- #
_TOC_RE = re.compile(r"^(?:índice|indice|sumário|sumario|conteúdo|conteudo|table of contents|contents)$", re.I)


def blocks_to_markdown(pages: list[tuple[int, list[dict]]], body: float | None = None,
                       page_markers: bool = False, page_starts: list | None = None) -> list[str]:
    sizes = [b["size"] for _, bl in pages for b in bl if b["kind"] == "line" for _ in range(max(1, len(b["text"]) // 8))]
    if not sizes:
        return []
    body = body or statistics.median(sizes)
    pages_of: dict[float, set[int]] = {}
    for n, bl in pages:
        for b in bl:
            if b["kind"] == "line" and b["size"] >= body * 1.15 and len(b["text"]) < 150 and not b.get("mono"):
                pages_of.setdefault(round(b["size"], 1), set()).add(n)
    head_sizes = sorted(pages_of, reverse=True)

    def group(sizes_desc: list[float]) -> list[float]:
        """Agrupa tamanhos parecidos (±4%) no mesmo nível."""
        out: list[float] = []
        for sz in sizes_desc:
            if not out or out[-1] - sz > out[-1] * 0.04:
                out.append(sz)
        return out

    # Tamanhos “estruturais” (que aparecem em 2 ou mais páginas) definem os níveis: fontes enormes
    # usadas uma vez só (capa, decoração) não ocupam os níveis dos títulos de verdade.
    structural = [sz for sz in head_sizes if len(pages_of[sz]) >= 2] if len(pages) > 2 else []
    levels = group(structural)[:3] if structural else group(head_sizes)[:3]

    # fontes maiores que os níveis (título do documento, capa) ficam em # e os níveis descem um
    offset = 1 if levels and any(sz > levels[0] * 1.04 for sz in head_sizes) else 0

    def level_of(size: float) -> int | None:
        if levels and size > levels[0] * 1.04:
            return 1
        for i, sz in enumerate(levels):
            if abs(size - sz) <= sz * 0.04 or size > sz:  # igual, ou entre dois níveis: fica com o de baixo
                return min(i + 1 + offset, 6)
        return None

    parts: list[str] = []
    for page_no, blocks in pages:
        first_part = len(parts)
        if page_markers:
            parts.append(f"<!-- Página {page_no + 1} -->")
        # página de índice/sumário: os itens viram lista e os números de página somem
        toc = any(b["kind"] == "line" and _TOC_RE.match(b["text"].strip()) for b in blocks)
        para: list[str] = []
        code: list[dict] = []
        prev = None
        prev_heading = False
        para_right = 0.0

        def flush_para():
            if para:
                parts.append(reflow("\n".join(para)))
                para.clear()

        def flush_code():
            if code:
                x_min = min(c["x0"] for c in code)
                cw = statistics.median([(c["x1"] - c["x0"]) / max(len(c["text"]), 1) for c in code]) or 5
                lines = [" " * int(round((c["x0"] - x_min) / cw)) + c["text"] for c in code]
                parts.append("```\n" + "\n".join(lines) + "\n```")
                code.clear()

        for k, b in enumerate(blocks):
            if b["kind"] != "line":
                flush_para()
                flush_code()
                parts.append(b["text"])
                prev = None
                continue
            text = b["text"].strip()
            if not text:
                continue
            if b.get("mono"):
                flush_para()
                code.append(b)
                prev = b
                continue
            flush_code()
            if toc and not _TOC_RE.match(text):
                if re.fullmatch(r"[\d\s.·…]+", text):
                    continue                            # número de página do índice
                flush_para()
                parts.append("- " + re.sub(r"[\s.·…]+\d+$", "", text))
                prev = b
                continue
            nxt = next((x for x in blocks[k + 1:k + 2] if x["kind"] == "line"), None)
            # continuação de um título que quebrou em duas linhas (mesmo tamanho, logo abaixo)
            cont = bool(prev_heading and parts and parts[-1].startswith("#") and abs(b["size"] - prev["size"]) < 0.5
                        and 0 <= b["top"] - prev["bottom"] < b["size"] * 0.5)
            lvl = level_of(b["size"])
            inferred = False
            section = _SECTION_RE.match(text) if b.get("bold") else None
            if lvl is None and b.get("bold") and len(text) < 90 and not text.endswith((".", ",", ";", ":")) \
                    and body * 0.92 < b["size"] < (levels[-1] * 0.96 if levels else body * 1.6) \
                    and not re.match(r"^[•\-–*]", text) and (section or not re.match(r"\d+[.)]\s", text)):
                lvl = len(levels) + 1 + offset   # negrito (corpo ou um pouco maior), sozinho na linha = subtítulo
                if section:                      # seção numerada: “4.1. Título” fica um nível abaixo de “4. Título”
                    lvl += section.group(1).count(".")
                inferred = True
            if lvl and not _can_be_heading(text, b, nxt, inferred, cont, body):
                lvl = None
            if lvl:
                flush_para()
                same = (parts and prev is not None and parts[-1].startswith("#" * lvl + " ")
                        and not parts[-1].startswith("#" * (lvl + 1))
                        and 0 <= b["top"] - prev["bottom"] < b["size"] * 0.5)
                if same:
                    parts[-1] += " " + text
                else:
                    parts.append("#" * min(lvl, 6) + " " + text)
                prev_heading = True
            else:
                if prev is not None and (b["top"] - prev["bottom"] > b["size"] * 0.9 or b["top"] < prev["top"] - 2):
                    flush_para()      # espaço grande ou mudança de coluna = novo parágrafo
                elif para and prev is not None and prev.get("kind") == "line" and _ends_paragraph(prev, para_right):
                    flush_para()      # linha anterior curta terminando em ponto = fim de parágrafo
                if not para:
                    para_right = b["x1"]
                para_right = max(para_right, b["x1"])
                para.append(text)
                prev_heading = False
            prev = b
        flush_para()
        flush_code()
        if page_starts is not None:
            new = [p for p in parts[first_part:] if not p.startswith(("<!--", "![", "```"))]
            if new:
                page_starts.append((page_no + 1, new[0]))
    return parts


# seção numerada em negrito (“1. Introdução”, “4.2 Resultados”): número curto + título curto sem ponto final
_SECTION_RE = re.compile(r"^(\d{1,2}(?:\.\d{1,2}){0,3})\.?\s+[A-ZÀ-Ý][^.!?;:]{1,70}$")
_NOT_HEADING = re.compile(r"@|https?://|www\.|\.(?:br|com|org|net|gov)(?:/|\b)", re.I)


def _can_be_heading(text: str, b: dict, nxt: dict | None, inferred: bool = True, cont: bool = False,
                    body: float = 0.0) -> bool:
    """Descarta falsos títulos: números soltos, letras soltas (logotipos), endereços de site/e-mail.
    Para os títulos deduzidos só pelo negrito (`inferred`), também descarta trechos em minúscula e a
    1ª linha de um parágrafo em negrito que continua embaixo. `cont`: continuação de um título."""
    letters = sum(c.isalpha() for c in text)
    if re.fullmatch(r"[\d\s.,/%-]+", text) or (letters < 2 and not cont):
        return False
    if _NOT_HEADING.search(text) and " " not in text.strip():
        return False
    if cont or not inferred:
        return True
    first = text.lstrip("\"'“(«")[:1]
    if first.islower():
        return False
    if nxt is not None and not text.rstrip().endswith((":", "?", "!")):
        gap = nxt["top"] - b["bottom"]
        nt = nxt["text"].strip()
        same_style = abs(nxt["size"] - b["size"]) < 0.5 and bool(nxt.get("bold")) == bool(b.get("bold"))
        body_size = not body or abs(b["size"] - body) < body * 0.08   # subtítulo maior que o corpo pode quebrar
        if same_style and 0 <= gap < b["size"] * 0.6 and nt[:1].islower() and body_size:
            return False                                 # frase em negrito quebrada em duas linhas
    return True


def _ends_paragraph(prev: dict, right: float) -> bool:
    text = prev["text"].rstrip()
    width = right - prev["x0"]
    return (text[-1:] in ".!?:" and width > 0 and prev["x1"] < right - width * 0.12)


def reflow(text: str) -> str:
    """Junta linhas quebradas em parágrafos e reconhece listas."""
    out: list[str] = []
    buf = ""
    for line in text.splitlines():
        line = line.strip()
        if not line:
            if buf:
                out.append(buf)
                buf = ""
            continue
        numbered = re.match(r"^\(?\d{1,3}[.)]\s", line)
        bullet = line[:1] in "•-–*▪●◦■" or bool(numbered)
        if line[:1] in "•▪●–◦■":
            line = "- " + line[1:].strip()
        if bullet and buf:
            out.append(buf)
            buf = line
        elif buf and buf.endswith("-") and not buf.endswith(" -") and line[:1].islower():
            buf = buf[:-1] + line
        elif buf and buf[-1:] in ".:!?;" and (line[:1].isupper() or line[:1].isdigit()) and len(buf) < 70:
            out.append(buf)
            buf = line
        else:
            buf = f"{buf} {line}" if buf else line
    if buf:
        out.append(buf)
    # itens de lista consecutivos ficam juntos
    merged: list[str] = []
    for p in out:
        if merged and p.startswith("- ") and merged[-1].split("\n")[-1].startswith("- "):
            merged[-1] += "\n" + p
        else:
            merged.append(p)
    return "\n\n".join(merged)


# --------------------------------------------------------------------------- #
# Conversor
# --------------------------------------------------------------------------- #
def convert_pdf(path: Path) -> str:
    try:
        import pdfplumber  # noqa: F401
        layout = option("pdf_layout", True)
    except ImportError:
        layout = False
    return _layout_pdf(path) if layout else _basic_pdf(path)


def _ocr_settings():
    from . import ocr

    mode = option("ocr", "auto")
    backend = ocr.pick_backend(option("ocr_backend", "auto")) if mode != "off" else None
    return mode, backend, option("ocr_lang", "por+eng")


def _ocr_page_blocks(page_image, scale: float, backend: str, lang: str) -> list[dict]:
    from .ocr import ocr_segments

    return ocr_segments(page_image, backend, lang, scale)


# carimbos e assinaturas que sistemas como PJe, SEI, eproc e e-SAJ repetem em todas as páginas
_STAMP = re.compile(
    r"assinado\s+(?:eletronicamente|digitalmente)|documento\s+assinado|n[úu]mero\s+do\s+documento\s*:|"
    r"c[óo]digo\s+verificador|c[óo]digo\s+crc|autenticidade\s+(?:deste|do)\s+documento|"
    r"(?:pje|sei|eproc|esaj|projudi)[\w./-]*\.(?:jus|gov)\.br|\bnum\.\s*\d+\s*-\s*p[áa]g\.\s*\d+|"
    r"este\s+documento\s+foi\s+gerado\s+pelo\s+usu[áa]rio|conferir\s+a\s+autenticidade",
    re.I)


def _is_stamp(text: str) -> bool:
    return len(text) < 400 and bool(_STAMP.search(text))


def _layout_pdf(path: Path) -> str:
    import pdfplumber

    from .core import check_cancel, report_partial, report_progress, warn
    from .ocr import mean_confidence

    from .converters import md_table

    sink = current_sink()
    mode, backend, lang = _ocr_settings()
    columns = option("pdf_columns", True)
    m_top = float(option("pdf_margin_top", 0) or 0) / 100
    m_bot = float(option("pdf_margin_bottom", 0) or 0) / 100
    want_images = sink is not None and sink.enabled
    strip_stamps = option("pdf_strip_stamps", True)
    ocr_pages = 0
    weak_ocr: list[tuple[int, float]] = []
    empty_pages: list[int] = []
    stamps: set[int] = set()
    try:
        pdf = pdfplumber.open(str(path))
        pdf.pages  # noqa: B018  - força a leitura (PDFs com senha falham aqui)
    except Exception as exc:  # noqa: BLE001
        text = f"{type(exc).__name__} {exc!r} {exc.__context__!r} {exc.__cause__!r}".lower()
        if "password" in text or "encrypt" in text:
            raise ConversionError(tr("PDF protegido por senha: abra-o com a senha e salve uma cópia sem "
                                  "proteção para converter.")) from exc
        raise
    with pdf:
        idx = parse_pages(option("pages", ""), len(pdf.pages))
        pages: list[tuple[int, list[dict]]] = []
        for k, i in enumerate(idx):
            check_cancel()
            report_progress(k, len(idx))
            page = pdf.pages[i]
            W, H = float(page.width), float(page.height)
            blocks: list[dict] = []
            page_gutter = None              # corredor entre colunas (achado pelas palavras, se houver texto)
            tables = page.find_tables() if option("pdf_tables", True) else []
            bboxes = []
            for t in tables:
                rows = t.extract(**WORD_GAP)
                if rows and max(len(r) for r in rows) >= 2 and len(rows) >= 2:
                    bboxes.append(t.bbox)
                    blocks.append({"kind": "table", "text": md_table(rows), "rows": rows, "x0": t.bbox[0], "x1": t.bbox[2],
                                   "top": t.bbox[1], "bottom": t.bbox[3]})

            def inside(obj, _b=bboxes):
                x = (obj["x0"] + obj["x1"]) / 2
                y = (obj["top"] + obj["bottom"]) / 2
                return any(b[0] <= x <= b[2] and b[1] <= y <= b[3] for b in _b)

            words = [w for w in page.extract_words(extra_attrs=["size", "fontname", "upright"],
                                                   keep_blank_chars=False, **WORD_GAP) if not inside(w)]
            if strip_stamps:
                # texto vertical nas laterais (faixa “Assinado eletronicamente por…” do PJe/SEI, carimbo do
                # arXiv): só quando forma uma frase longa — rótulos curtos de gráficos ficam
                for side in ("esq", "dir"):
                    lateral = [w for w in words if not w.get("upright", True)
                               and ((w["x0"] + w["x1"]) / 2 < W * 0.15 if side == "esq"
                                    else (w["x0"] + w["x1"]) / 2 > W * 0.85)]
                    if sum(len(w["text"]) for w in lateral) >= 30:
                        gone = {id(w) for w in lateral}
                        words = [w for w in words if id(w) not in gone]
                        stamps.add(i)
            # texto da página inclui o das tabelas: página só com tabela não é “escaneada” (senão o OCR
            # repetia a tabela inteira como texto solto)
            n_chars = sum(len(w["text"]) for w in words) + sum(len(b["text"]) for b in blocks if b["kind"] == "table")
            use_ocr = backend is not None and (mode == "force" or (mode == "auto" and n_chars < 25))
            if use_ocr:
                from .safety import safe_resolution

                img = page.to_image(resolution=safe_resolution(W, H, 300)).original
                blocks = [b for b in blocks if b["kind"] == "table"] if mode != "force" else []
                from .ocr import OcrTimeout

                try:
                    segs = _ocr_page_blocks(img, 72 / 300, backend, lang)
                except OcrTimeout as exc:                 # página patológica: segue com as outras
                    warn(f"{exc} ({tr('página {0}').format(i + 1)})", [i + 1])
                    segs = []
                blocks += segs
                ocr_pages += 1
                conf = mean_confidence(segs)
                if conf is not None and conf < 70:
                    weak_ocr.append((i + 1, conf))
                elif conf is None:
                    empty_pages.append(i + 1)
            else:
                page_gutter = word_gutter(words, W) if columns else None
                segs = words_to_segments(words, page_gutter)
                if option("pdf_tables", True):
                    found, segs = borderless_tables(segs, W)      # tabelas sem linhas desenhadas
                    blocks += found
                blocks += segs
                if want_images:
                    for im in page.images:
                        x0, top, x1, bottom = (max(0, im["x0"]), max(0, im["top"]), min(W, im["x1"]), min(H, im["bottom"]))
                        if (x1 - x0) < 40 or (bottom - top) < 40:
                            continue
                        try:
                            from .safety import safe_resolution

                            pil = page.crop((x0, top, x1, bottom)).to_image(
                                resolution=safe_resolution(x1 - x0, bottom - top, 150)).original
                        except Exception:  # noqa: BLE001
                            continue
                        ref = sink.add_pil(pil, tr('Imagem da página {0}').format(i + 1))
                        if ref:
                            blocks.append({"kind": "image", "text": ref, "x0": x0, "x1": x1,
                                           "top": top, "bottom": bottom})
            for b in blocks:
                b["margin"] = b["top"] < H * 0.08 or b["bottom"] > H * 0.92
            if strip_stamps:
                kept = [b for b in blocks if not (b["kind"] == "line" and _is_stamp(b["text"])
                                                  and (b["margin"] or b["x0"] > W * 0.8 or b["x1"] < W * 0.2))]
                if len(kept) < len(blocks):
                    stamps.add(i)
                    blocks = kept
            if not use_ocr and n_chars < 25 and not any(b["kind"] == "table" for b in blocks):
                empty_pages.append(i + 1)
            if m_top or m_bot:
                blocks = [b for b in blocks if b["top"] >= H * m_top and b["bottom"] <= H * (1 - m_bot)]
            ordered = reading_order(blocks, W, columns, page_gutter)
            pages.append((i, ordered))
            # prévia: texto provisório da página (títulos e tabelas são arrumados no fim)
            report_partial(i + 1, "\n\n".join(b["text"] for b in ordered
                                               if b.get("kind") != "image" and b.get("text")))
        meta_title = (pdf.metadata or {}).get("Title")
        report_progress(len(idx), len(idx))
    if weak_ocr:
        pg = [p for p, _ in weak_ocr]
        avg = sum(c for _, c in weak_ocr) / len(weak_ocr)
        warn(tr('OCR com baixa confiança ({0:.0f}%) na(s) página(s) {1}: revise o texto.').format(avg, _pages_text(pg)), pg)
    if empty_pages:
        hint = "" if backend else tr(" Escaneada? O OCR está desligado ou indisponível.")
        warn(tr('Nenhum texto reconhecido na(s) página(s) {0}.{1}').format(_pages_text(empty_pages), hint), empty_pages)
    if stamps:
        warn(tr('Carimbos/assinaturas eletrônicas repetidos (PJe, SEI…) removidos em {0} página(s).').format(len(stamps)),
             info=True)

    if option("pdf_strip_headers", True):
        rep = repeated_lines([[b["text"] for b in bl if b["kind"] == "line" and b["margin"]] for _, bl in pages],
                             edge=10)
        if rep:
            pages = [(n, [b for b in bl if not (b["kind"] == "line" and b["margin"] and _key(b["text"]) in rep)])
                     for n, bl in pages]

    if option("pdf_merge_tables", True):
        pages, merged = merge_split_tables(pages)
        if merged:
            warn(tr("{0} tabela(s) que continuavam na página seguinte foram juntadas.").format(merged), info=True)

    starts: list = []
    parts = blocks_to_markdown(pages, page_markers=option("pdf_page_markers", False), page_starts=starts)
    from .core import record_page_starts

    record_page_starts(starts)
    if not parts:
        return f"# {_title(meta_title, path)}\n\n{NO_TEXT}"
    if not any(p.startswith("# ") for p in parts):
        parts.insert(0, f"# {_title(meta_title, path)}")
    if ocr_pages:
        parts.append(f"<!-- Markinho: {ocr_pages} página(s) reconhecida(s) por OCR ({backend}) -->")
    return "\n\n".join(parts)


# linhas que podem ficar entre os dois pedaços de uma tabela: número de página e avisos de continuação
_TABLE_CONT = re.compile(r"^[\s\d/–-]*$|^\(?\s*(continua|continuação|cont\.|continued|continúa|continuación)\b",
                         re.I)


def _norm_row(row) -> tuple:
    return tuple(re.sub(r"\s+", " ", str(c or "")).strip().lower() for c in row)


def merge_split_tables(pages: list[tuple[int, list[dict]]]) -> tuple[list[tuple[int, list[dict]]], int]:
    """Junta a tabela que termina uma página com a que começa a seguinte, quando têm o mesmo número de
    colunas (uma tabela longa que quebrou entre páginas). O cabeçalho repetido no alto da página nova sai.
    Assim a tabela fica inteira no Markdown e nos pedaços para IA (RAG). Devolve (páginas, nº de junções)."""
    from .converters import md_table

    def edge(blocks: list[dict], last: bool) -> int | None:
        order = range(len(blocks) - 1, -1, -1) if last else range(len(blocks))
        for k in order:
            b = blocks[k]
            if b["kind"] == "table":
                return k if b.get("rows") else None
            if b["kind"] == "line" and (b.get("margin") or _TABLE_CONT.match(b["text"].strip())):
                continue                                  # rodapé, número de página, “(continua)”
            return None
        return None

    def width(rows) -> int:
        return max(len(r) for r in rows)

    out = [(n, list(bl)) for n, bl in pages]
    merged = 0
    host: tuple[int, int] | None = None          # (página, bloco) da tabela que pode continuar
    for k, (n, blocks) in enumerate(out):
        j = edge(blocks, False) if host is not None and n == out[k - 1][0] + 1 else None
        if j is not None:
            hp, hi = host
            top, cont = out[hp][1][hi]["rows"], blocks[j]["rows"]
            if width(top) == width(cont):
                if _norm_row(cont[0]) == _norm_row(top[0]):
                    cont = cont[1:]                          # cabeçalho repetido na página nova
                rows = top + cont
                out[hp][1][hi] = {**out[hp][1][hi], "rows": rows, "text": md_table(rows)}
                # sai a continuação e o que estava antes dela (rodapé, “continua”); imagens ficam
                blocks = [b for x, b in enumerate(blocks) if x > j or (x < j and b["kind"] != "line")]
                out[k] = (n, blocks)
                merged += 1
                if not any(b["kind"] != "line" or not (b.get("margin") or _TABLE_CONT.match(b["text"].strip()))
                           for b in blocks):
                    continue              # a página era só a continuação: a tabela pode seguir na próxima
        i = edge(blocks, True)
        host = (k, i) if i is not None else None
    return out, merged


def _pages_text(pages: list[int], limit: int = 12) -> str:
    txt = ", ".join(map(str, pages[:limit]))
    return txt + (tr(' e mais {0}').format(len(pages) - limit) if len(pages) > limit else "")


def _basic_pdf(path: Path) -> str:
    """Extração simples com pypdf (sem pdfplumber)."""
    from pypdf import PdfReader

    reader = PdfReader(str(path))
    if reader.is_encrypted:
        try:
            reader.decrypt("")
        except Exception as exc:  # noqa: BLE001
            raise ConversionError(tr("PDF protegido por senha.")) from exc
    idx = parse_pages(option("pages", ""), len(reader.pages))
    texts = [(i, (reader.pages[i].extract_text() or "").strip()) for i in idx]
    rep = repeated_lines([t.splitlines() for _, t in texts]) if option("pdf_strip_headers", True) else set()
    parts = [f"# {_title(reader.metadata.title if reader.metadata else None, path)}"]
    starts: list = []
    for i, text in texts:
        if rep:
            text = "\n".join(ln for ln in text.splitlines() if _key(ln) not in rep)
        if not text.strip():
            continue
        if option("pdf_page_markers", False):
            parts.append(f"<!-- Página {i + 1} -->")
        parts.append(reflow(text))
        starts.append((i + 1, parts[-1]))
    from .core import record_page_starts

    record_page_starts(starts)
    if len(parts) == 1:
        parts.append(NO_TEXT)
    return "\n\n".join(parts)


def convert_image(path: Path) -> str:
    """Imagem (PNG, JPG, TIFF…): OCR do texto + a própria imagem como ativo."""
    from PIL import Image, ImageOps

    from . import ocr

    sink = current_sink()
    mode, backend, lang = _ocr_settings()
    with Image.open(path) as im:
        frames = []
        try:
            n = getattr(im, "n_frames", 1)
        except Exception:  # noqa: BLE001
            n = 1
        for f in range(min(n, 50)):   # TIFF de várias páginas
            im.seek(f)
            frames.append(ImageOps.exif_transpose(im.copy()))
    parts = [f"# {path.stem}"]
    for k, img in enumerate(frames):
        if sink is not None and sink.enabled and option("image_embed_original", True):
            ref = sink.add_pil(img if img.mode in ("RGB", "RGBA", "L") else img.convert("RGB"), path.stem)
            if ref:
                parts.append(ref)
        if backend is None:
            parts.append(f"_Sem OCR: {ocr.describe_status()}_")
            continue
        # imagens pequenas são ampliadas: o OCR erra muito com letras de poucos pixels
        scale = 1.0
        if img.width < 1500:
            scale = min(3.0, 1500 / max(img.width, 1))
            img = img.resize((int(img.width * scale), int(img.height * scale)))
        kind = option("image_mode", "auto")
        if kind == "table":                       # “Ler imagem como tabela”
            from .converters import md_table

            rows = ocr.words_to_table(ocr.ocr_words(img, backend, lang))
            parts.append(md_table(rows) if len(rows) >= 1 and max(len(r) for r in rows) >= 2
                         else "\n".join(" ".join(r) for r in rows) or tr("_Nenhum texto reconhecido na imagem._"))
            continue
        if kind == "code":                        # “Ler imagem como código” (mantém espaços)
            code = ocr.ocr_code(img, backend, lang)
            parts.append(f"```\n{code}\n```" if code.strip() else tr("_Nenhum texto reconhecido na imagem._"))
            continue
        segs = ocr.ocr_segments(img, backend, lang, 1 / scale)
        if kind == "text":                        # texto corrido, sem detectar títulos
            text = "\n".join(s["text"] for s in sorted(segs, key=lambda s: (s["top"], s["x0"])))
            parts.append(text or tr("_Nenhum texto reconhecido na imagem._"))
            continue
        conf = ocr.mean_confidence(segs)
        if conf is not None and conf < 70:
            from .core import warn

            warn(tr('OCR com baixa confiança ({0:.0f}%) na imagem{1}: revise o texto (foto tremida, escura ou com letras pequenas?).').format(conf, f' {k + 1}' if len(frames) > 1 else ''), [k + 1])
        body = reading_order(segs, img.width / scale, option("pdf_columns", True))
        text = blocks_to_markdown([(k, body)])
        parts += text or [tr("_Nenhum texto reconhecido na imagem._")]
    return "\n\n".join(parts)
