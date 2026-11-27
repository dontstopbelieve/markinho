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


def _word_rows(words: list[dict]) -> list[list[dict]]:
    """Palavras agrupadas por linha (mesma altura), cada linha da esquerda para a direita."""
    rows: list[list[dict]] = []
    for w in sorted(words, key=lambda w: (round(w["top"]), w["x0"])):
        size = w.get("size", 10) or 10
        for row in reversed(rows[-4:]):
            ref = row[0]
            if abs(w["top"] - ref["top"]) <= 0.45 * min(size, ref.get("size", size) or size) \
                    or abs(w["bottom"] - ref["bottom"]) <= 0.3 * size:
                row.append(w)
                break
        else:
            rows.append([w])
    for row in rows:
        row.sort(key=lambda w: w["x0"])
    return rows


def column_rivers(words: list[dict], width: float, min_rows: int = 6,
                  min_words: int = 3) -> list[tuple[float, float, float]]:
    """Corredores entre colunas achados pelas palavras: posições x que caem num vão entre palavras em pelo
    menos `min_rows` linhas seguidas (sem nenhuma palavra por cima). Acha 2, 3 ou mais colunas e corredores
    que só existem em parte da página (título ou figura atravessando). Devolve (x, topo, base) de cada um.
    Vãos de texto justificado não formam corredor: mudam de lugar de uma linha para outra."""
    body = [w for w in words if w.get("upright", True) and (w["x1"] - w["x0"]) < width * 0.4]
    if len(body) < (30 if min_words > 1 else 12) or width <= 0:
        return []
    rows = _word_rows(body)
    if len(rows) < min_rows:
        return []
    W = int(width) + 2
    # 0 = palavra (ou espaço comum entre palavras), 1 = vão largo entre palavras, 2 = fora da linha
    grid = []
    for row in rows:
        st = bytearray([2]) * W
        size = statistics.median(w.get("size", 10) or 10 for w in row)
        need = max(3.0, 0.45 * size)
        x_first, x_last = int(row[0]["x0"]), int(max(w["x1"] for w in row)) + 1
        for x in range(max(0, x_first), min(W, x_last)):
            st[x] = 0
        for a, b in zip(row, row[1:]):
            if b["x0"] - a["x1"] >= need:
                for x in range(max(0, int(a["x1"]) + 1), min(W, int(b["x0"]))):
                    st[x] = 1
        grid.append(st)
    found: list[tuple[int, int, int, int]] = []          # (x, linha inicial, linha final, linhas com vão)
    for x in range(int(width * 0.08), int(width * 0.92)):
        start, count, last_gap = None, 0, None
        for r in range(len(rows) + 1):
            v = grid[r][x] if r < len(rows) else 0
            if v == 0:
                if start is not None and count >= min_rows:
                    found.append((x, start, r - 1, count))     # até o fim da faixa vazia (coluna mais longa)
                start, count, last_gap = None, 0, None
            else:
                if start is None:
                    start = r
                if v == 1:
                    count += 1
                    last_gap = r
    if not found:
        return []
    # junta posições vizinhas do mesmo corredor (x a 1 pt e linhas em comum); fica a do meio
    groups: list[list[tuple[int, int, int, int]]] = []
    for f in sorted(found):
        for g in groups:
            if any(abs(f[0] - h[0]) <= 1 and not (f[2] < h[1] or f[1] > h[2]) for h in g[-3:]):
                g.append(f)
                break
        else:
            groups.append([f])

    def pieces(row: list[dict]) -> list[list[dict]]:
        """A linha cortada em todos os vãos largos: cada pedaço é um trecho de texto corrido."""
        size = statistics.median(w.get("size", 10) or 10 for w in row)
        need = max(3.0, 0.45 * size)
        out = [[row[0]]]
        for a, b in zip(row, row[1:]):
            if b["x0"] - a["x1"] >= need:
                out.append([b])
            else:
                out[-1].append(b)
        return out

    rivers = []
    for g in groups:
        best = max(c for *_, c in g)
        xs = sorted((f for f in g if f[3] >= best * 0.8), key=lambda f: f[0])
        x, r0, r1 = xs[len(xs) // 2][0], min(f[1] for f in xs), max(f[2] for f in xs)
        # dos dois lados, logo junto do corredor, precisa haver texto corrido (colunas) — não um número de
        # referência “[36]”, um horário ou um rótulo
        lefts, rights = [], []
        for row in rows[r0:r1 + 1]:
            ps = pieces(row)
            lp = [pc for pc in ps if pc[-1]["x1"] <= x]
            rp = [pc for pc in ps if pc[0]["x0"] >= x]
            if lp and rp:
                lefts.append((len(lp[-1]), lp[-1][-1]["x1"] - lp[-1][0]["x0"]))
                rights.append((len(rp[0]), rp[0][-1]["x1"] - rp[0][0]["x0"]))
        if len(lefts) < min_rows:
            continue
        ln = statistics.median(n for n, _ in lefts)
        rn = statistics.median(n for n, _ in rights)
        lwid = statistics.median(v for _, v in lefts)
        rwid = statistics.median(v for _, v in rights)
        # largura mínima de coluna: 8% da página e uns 12 caracteres (guia de TV, dicionário em letra miúda)
        size = statistics.median(w.get("size", 10) or 10 for row in rows[r0:r1 + 1] for w in row)
        need_w = max(width * 0.08, 12 * size * 0.5 * 2)
        if ln >= min_words and rn >= min_words and lwid >= need_w and rwid >= need_w:
            rivers.append((float(x) + 0.5, rows[r0][0]["top"] - 1, max(w["bottom"] for w in rows[r1]) + 1))
    # o mesmo corredor um pouco deslocado (recuo de parágrafo ou de referência): fica o mais comprido
    rivers.sort(key=lambda r: r[2] - r[1], reverse=True)
    kept: list[tuple[float, float, float]] = []
    for r in rivers:
        if not any(abs(r[0] - k[0]) < 20 and not (r[2] < k[1] or r[1] > k[2]) for k in kept):
            kept.append(r)
    rivers = sorted(kept)
    return rivers


def words_to_segments(words: list[dict], split_x: float | None = None, gap: float | None = None,
                      rivers: list[tuple[float, float, float]] | None = None) -> list[dict]:
    """Agrupa palavras em linhas e quebra a linha onde há um vão grande (colunas). `split_x`: corredor entre
    colunas (de `word_gutter`) — a linha é quebrada ali mesmo que o vão seja estreito. `rivers`: corredores de
    `column_rivers` (x, topo, base), que valem só na altura em que existem."""
    rows = _word_rows(words)
    segs = []
    for row in rows:
        top = row[0]["top"]
        cuts = [x for x, t, b in (rivers or ()) if t <= top <= b]
        if split_x is not None:
            cuts.append(split_x)
        cur = [row[0]]
        for w in row[1:]:
            size = statistics.median([c.get("size", 10) or 10 for c in cur])
            crosses = any(cur[-1]["x1"] <= x + 1 and w["x0"] >= x - 1 for x in cuts)
            limit = gap * size if gap else max(1.8 * size, 14)     # `gap`: separação mais fina (tabelas)
            if crosses or w["x0"] - cur[-1]["x1"] > limit:
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


# número de página sozinho: “12”, “- 12 -”, “xii”, “Página 3 de 10”, “page 64”, “3 / 15”
_PAGE_NO = re.compile(r"^(?:[-–—\s]*\d{1,4}[-–—\s]*|[ivxlcdm]{1,6}|p(?:á|a)g(?:ina)?\.?\s*\d+(?:\s*(?:de|of|/)\s*\d+)?|"
                      r"page\s+\d+(?:\s+of\s+\d+)?|\d{1,4}\s*/\s*\d{1,4}|\d{1,4}\s+(?:of|de|von|di)\s+\d{1,4})$", re.I)
# cara de cabeçalho/rodapé: site, DOI, ISSN/ISBN, volume/número de revista, ©, avisos de citação e impressão
_FURNITURE = re.compile(
    r"www\.|https?://|\bdoi\b|\bissn\b|\bisbn\b|\bvol(?:ume)?\.?\s*\d|\bissue\s*\d|\bno\.\s*\d|©|"
    r"\(\d+pp\)|\b\d+\s*[:(]\s*\d+[-–]\d+|\d{4};\s*\d+\(|all rights reserved|todos os direitos|"
    r"please cite|cite this article|downloaded from|terms of use|printed:|impresso em|\bet al\.\s*:|"
    r"\bjournal\b|\brevista\b|\bproceedings\b|data de (?:edição|publicação)|"
    # citação da revista: “Microorganisms 2021, 9, 1042”, “24, 1–9”, “7(2):126–134”
    r"\b(?:19|20)\d\d\s*,\s*\d+\s*,\s*\d+|\b\d+\s*,\s*\d+\s*[-–]\s*\d+\s*,|\(\d+\)\s*:?\s*\d+\s*[-–]\s*\d+", re.I)
_MONTH_DATE = re.compile(r"\b(?:jan|feb|fev|mar|apr|abr|may|mai|jun|jul|aug|ago|sep|set|oct|out|nov|dec|dez)[a-zç]*\.?"
                         r"\s+\d{1,2},?\s+(?:19|20)\d\d\b|\b\d{1,2}\s+(?:de\s+)?(?:jan|fev|feb|mar|abr|apr|mai|may|jun|"
                         r"jul|ago|aug|set|sep|out|oct|nov|dez|dec)[a-zç]*\.?\s+(?:de\s+)?(?:19|20)\d\d\b", re.I)


def _flat_cell(text) -> str | None:
    """Célula de tabela de PDF: a quebra de linha é só o texto que não coube na largura — junta as linhas e
    emenda a palavra hifenizada (“Grund-⏎skola” → “Grundskola”)."""
    if text is None:
        return None
    text = re.sub(r"(\w)-\n(?=[a-zà-ÿ])", r"\1", str(text))
    return re.sub(r"\s*\n\s*", " ", text).strip()


_CAPTION = re.compile(r"^(?:table|tabela|tabla|tableau|figure|figura|fig\.|quadro|gráfico|chart|exhibit)\s*[\dIVX]",
                      re.I)


def _rows(lines: list[dict]) -> list[list[dict]]:
    """Agrupa as linhas que estão na mesma altura (ex.: “13816” à esquerda e “Boletín Oficial…” à direita)."""
    rows: list[list[dict]] = []
    for b in sorted(lines, key=lambda b: b["top"]):
        if rows:
            r = rows[-1]
            top, bottom = min(x["top"] for x in r), max(x["bottom"] for x in r)
            overlap = min(bottom, b["bottom"]) - max(top, b["top"])
            if overlap >= 0.5 * min(bottom - top, b["bottom"] - b["top"]):
                r.append(b)
                continue
        rows.append([b])
    return rows


def strip_page_furniture(blocks: list[dict], height: float) -> list[dict]:
    """Cabeçalho e rodapé de UMA página (sem precisar que se repitam): a partir de cada beira (10% de cima e de
    baixo; 12% para a primeira faixa), até 4 faixas seguidas que sejam número de página, tenham cara de rodapé
    (site, DOI, “Vol. 19”, “Please cite…”), letra menor que a do texto ou sejam o título corrido bem separado do
    texto. Linhas na mesma altura contam juntas (cabeçalho com partes à esquerda e à direita). Para na primeira
    faixa que é texto de verdade. Título (letra grande), nota de rodapé (“1 Ver…”) e o corpo ficam."""
    lines = [b for b in blocks if b["kind"] == "line"]
    if len(lines) < 2:
        return blocks
    body = statistics.median(b["size"] for b in lines)
    rows = _rows(lines)
    drop: set[int] = set()

    def strong(row: list[dict]) -> bool:
        """Faixa que é rodapé sem dúvida: número de página ou cara de rodapé (site, DOI, citação da revista)."""
        pieces = [b["text"].strip() for b in row]
        text = " ".join(pieces)
        if _CAPTION.match(text) or not text:
            return False
        if all(_PAGE_NO.match(t) for t in pieces):
            return True
        size = max((b["size"] for b in row if not _PAGE_NO.match(b["text"].strip())), default=body)
        return ((bool(_FURNITURE.search(text)) and len(text) <= 200) or
                (bool(_MONTH_DATE.search(text)) and len(text) <= 90)) and size <= body * 1.4

    for edge in ("top", "bottom"):
        ordered = rows if edge == "top" else rows[::-1]
        for k, row in enumerate(ordered[:4]):
            top, bottom = min(b["top"] for b in row), max(b["bottom"] for b in row)
            mid = (top + bottom) / 2
            band = 0.12 if k == 0 else 0.1
            if not (mid < height * band if edge == "top" else mid > height * (1 - band)):
                break
            pieces = [b["text"].strip() for b in sorted(row, key=lambda b: b["x0"])]
            text = " ".join(pieces)
            if _CAPTION.match(text):
                break                                     # legenda de tabela/figura é conteúdo
            # o número de página ao lado (às vezes em letra grande) não conta no tamanho
            size = max((b["size"] for b in row if not _PAGE_NO.match(b["text"].strip())), default=body)
            # folga até a próxima faixa que não seja rodapé óbvio (“CERN/DG/RB…” seguido de “Page 10”)
            nxt = next((r for r in ordered[k + 1:] if not strong(r)), None)
            if nxt:
                gap = (min(b["top"] for b in nxt) - bottom) if edge == "top" else (top - max(b["bottom"] for b in nxt))
            else:
                gap = 99
            if strong(row):
                drop.update(id(b) for b in row)
                continue
            small = (size <= body * 0.92 and not any(b.get("bold") for b in row) and len(text) <= 160
                     and (k == 0 or gap >= size))
            footnote = edge == "bottom" and bool(re.match(r"^[\d*†‡¹²³⁴⁵⁶⁷⁸⁹]{1,2}\s*\S", text)) and len(text) > 30
            # título corrido: curto, letra de texto e bem afastado; com partes dos dois lados ou número de
            # página junto, pode ser um pouco maior
            split = len(row) > 1 or any(_PAGE_NO.match(t) for t in pieces)
            running = (k == 0 and len(text) <= (120 if split else 80) and size <= body * 1.1
                       and gap >= size * (0.8 if split else 1.2))
            if (running and not footnote) or (small and not footnote and gap >= size * 0.3):
                drop.update(id(b) for b in row)
            else:
                break
        # segunda passada: faixa óbvia logo depois de uma palavra solta (“ARTICLE” / “NATURE COMMUNICATIONS | DOI…”)
        for k, row in enumerate(ordered[:3]):
            mid = (min(b["top"] for b in row) + max(b["bottom"] for b in row)) / 2
            if not (mid < height * 0.1 if edge == "top" else mid > height * 0.9):
                break
            if strong(row):
                drop.update(id(b) for b in row)
    if len(drop) > max(3, len(lines) // 4):           # cautela: nunca tira mais de 1/4 das linhas da página
        return blocks
    return [b for b in blocks if id(b) not in drop]


def _columns_from_words(words: list[dict], row_tops: list[float], box: tuple[float, float, float, float]):
    """Refaz as células de uma tabela pelos corredores verticais das PALAVRAS da região inteira: colunas de
    números a meio espaço de distância (“0.763 0.030”) não grudam. Devolve as linhas ou None."""
    x0, x1, top, bottom = box
    inner = [w for w in words if x0 - 1 <= (w["x0"] + w["x1"]) / 2 <= x1 + 1
             and top - 1 <= (w["top"] + w["bottom"]) / 2 <= bottom + 1]
    if len(inner) < 6:
        return None
    size = statistics.median(w.get("size", 10) or 10 for w in inner)
    need = max(2.0, size * 0.35)
    # junta os intervalos [x0, x1] das palavras (posições exatas, sem arredondar): os vãos que sobram, de
    # cima a baixo da tabela, separam as colunas
    seps, end = [], None
    for x0, x1 in sorted((w["x0"], w["x1"]) for w in inner):
        if end is not None and x0 - end >= need:
            seps.append((end + x0) / 2)
        end = x1 if end is None else max(end, x1)
    if not 1 <= len(seps) <= 14:
        return None
    grid = [[[] for _ in range(len(seps) + 1)] for _ in row_tops]
    for w in sorted(inner, key=lambda w: w["x0"]):
        r = min(range(len(row_tops)), key=lambda k: abs(row_tops[k] - w["top"]))
        c = sum(1 for sx in seps if (w["x0"] + w["x1"]) / 2 > sx)
        grid[r][c].append(w["text"])
    rows = [[" ".join(cell) for cell in r] for r in grid if any(r)]
    return rows if len(rows) >= 2 else None


def borderless_tables(segs: list[dict], width: float, fine: list[dict] | None = None,
                      words: list[dict] | None = None) -> tuple[list[dict], list[dict]]:
    """Tabelas SEM linhas desenhadas, achadas pelo alinhamento: 3+ linhas seguidas com 2+ células curtas cada,
    cujas colunas caem nos mesmos lugares. Devolve (blocos de tabela, segmentos que sobraram).
    Texto em colunas (linhas compridas), listas de uma coluna e sumários com pontinhos ficam de fora."""
    from .converters import md_table

    if any(sg["kind"] == "line" and _TOC_RE.match(sg["text"].strip()) for sg in segs):
        return [], segs                       # página de índice/sumário: vira lista (blocks_to_markdown)
    coarse = segs
    if fine is not None:
        # procura as tabelas nas linhas quebradas com vão mais fino (colunas a ~1 letra de distância);
        # o texto que não for tabela continua com as linhas normais
        segs = fine
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
        last_cells = i                        # última linha com 2+ células

        def single(r):                        # linha de uma célula só: continuação de célula ou seção
            return (len(r) == 1 and r[0]["kind"] == "line" and r[0]["x1"] - r[0]["x0"] < width * 0.3
                    and not r[0].get("mono"))

        while j < len(rows) and rows[j][0]["top"] - rows[j - 1][0]["bottom"] < 2.5 * max(rows[j][0]["size"], 1):
            if cell_row(rows[j]):
                last_cells = j
            elif not (single(rows[j]) and j - last_cells <= 2):
                break
            j += 1
        j = last_cells + 1                    # a tabela não termina numa linha solta
        group = rows[i:j]
        if len(group) >= 3 and sum(1 for r in group if len(r) >= 2) >= 2:
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
                nwords = sorted(len(t.split()) for t in texts)
                numeric = sum(1 for t in texts if re.fullmatch(r"[\d\s.,%$€£R()+\-–/:]+", t)) / max(1, len(texts))
                short = nwords[len(nwords) // 2] <= 3 or numeric >= 0.3
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
                    box = (min(sg["x0"] for r in group for sg in r), max(sg["x1"] for r in group for sg in r),
                           group[0][0]["top"], max(sg["bottom"] for sg in group[-1]))
                    if words is not None:   # células pelas colunas da tabela inteira (mais precisas)
                        refined = _columns_from_words(words, [min(sg["top"] for sg in r) for r in group], box)
                        if refined and len(refined[0]) >= len(table_rows[0]):
                            table_rows = refined
                    tables.append({"kind": "table", "text": md_table(table_rows), "rows": table_rows,
                                   "x0": min(sg["x0"] for r in group for sg in r),
                                   "x1": max(sg["x1"] for r in group for sg in r),
                                   "top": group[0][0]["top"], "bottom": max(sg["bottom"] for sg in group[-1])})
                    used.update(id(sg) for r in group for sg in r)
        i = j
    if fine is None:
        return tables, [sg for sg in segs if id(sg) not in used]

    def inside(sg) -> bool:
        cx, cy = (sg["x0"] + sg["x1"]) / 2, (sg["top"] + sg["bottom"]) / 2
        return any(t["x0"] - 1 <= cx <= t["x1"] + 1 and t["top"] - 1 <= cy <= t["bottom"] + 1 for t in tables)

    return tables, [sg for sg in coarse if not inside(sg)]


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


def river_order(blocks: list[dict], width: float, rivers: list[tuple[float, float, float]]) -> list[dict]:
    """Ordem de leitura pelos corredores entre colunas (de `column_rivers`): na altura de cada corredor,
    lê-se coluna por coluna; um título ou figura que atravessa o corredor separa a parte de cima da de baixo.
    Funciona com 2, 3 ou mais colunas. Sem corredores, usa a ordem de sempre."""
    if not rivers:
        return reading_order(blocks, width, True)
    blocks = sorted(blocks, key=lambda b: (b["top"], b["x0"]))

    def key(b: dict):
        mid = (b["top"] + b["bottom"]) / 2
        active = [k for k, (x, t, bt) in enumerate(rivers) if t <= mid <= bt]
        if any(b["x0"] < rivers[k][0] - 1 and b["x1"] > rivers[k][0] + 1 for k in active):
            return None                                   # atravessa: fica sozinho, na ordem de cima para baixo
        return tuple(active)

    out: list[dict] = []
    zone: list[dict] = []
    zkey = ()

    def flush():
        if not zone:
            return
        if not zkey:
            out.extend(zone)
        else:
            cuts = sorted(rivers[k][0] for k in zkey)
            cols: list[list[dict]] = [[] for _ in range(len(cuts) + 1)]
            for b in zone:
                mid = (b["x0"] + b["x1"]) / 2
                cols[sum(1 for c in cuts if mid > c)].append(b)
            for col in cols:
                out.extend(sorted(col, key=lambda b: b["top"]))
        zone.clear()

    for b in blocks:
        k = key(b)
        if k is None:
            flush()
            out.append(b)
            zkey = ()
            continue
        if k != zkey:
            flush()
            zkey = k
        zone.append(b)
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
        if not any(bl for _, bl in pages):
            return []
        sizes = [10.0]                    # páginas só com tabelas/imagens (sem linha de texto solta)
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
    choice = option("ocr_backend", "auto")
    backend = ocr.pick_backend(choice) if mode != "off" else None
    if backend is not None and choice == "auto":
        backend = "auto"                  # o OCR escolhe por página (Tesseract ou PP-OCR para letra miúda)
    return mode, backend, option("ocr_lang", "auto")


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
            rivers: list = []
            tables = page.find_tables() if option("pdf_tables", True) else []
            bboxes = []
            for t in tables:
                rows = [[_flat_cell(c) for c in r] for r in (t.extract(**WORD_GAP) or [])]
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
                if columns:                               # colunas da página escaneada, pelas linhas lidas
                    rivers = column_rivers([dict(x, upright=True) for x in segs if x.get("kind") == "line"],
                                           W, min_words=1)
                conf = mean_confidence(segs)
                if conf is not None and conf < 70:
                    weak_ocr.append((i + 1, conf))
                elif conf is None:
                    empty_pages.append(i + 1)
            else:
                page_gutter = word_gutter(words, W) if columns else None
                rivers = column_rivers(words, W) if columns else []
                segs = words_to_segments(words, page_gutter, rivers=rivers)
                if option("pdf_tables", True):                    # tabelas sem linhas desenhadas
                    found, segs = borderless_tables(segs, W, words_to_segments(words, page_gutter, gap=1.0,
                                                                                rivers=rivers), words)
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
            if option("pdf_strip_headers", True):
                blocks = strip_page_furniture(blocks, H)
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
            # com corredores achados pelas palavras (2, 3 ou mais colunas), a ordem segue os corredores
            ordered = (river_order(blocks, W, rivers) if columns and rivers
                       else reading_order(blocks, W, columns, page_gutter))
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
