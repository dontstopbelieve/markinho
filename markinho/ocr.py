# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 dontstopbelieve — Markinho
"""OCR 100% local para imagens e PDFs escaneados.

* **Tesseract** – preserva os acentos do português (recomendado). Usa o executável
  instalado no sistema ou o que vem dentro do instalador do Markinho (Windows).
* **RapidOCR** – só Python (ONNX), não precisa instalar nada, mas o modelo padrão é
  chinês/inglês e costuma perder acentos ("Relatorio" em vez de "Relatório").

`ocr_lines` devolve linhas com posição e altura, para o mesmo montador de
Markdown usado nos PDFs (títulos, colunas, parágrafos).
"""
from __future__ import annotations

from .i18n import tr

import os
import shutil
import sys
from functools import lru_cache
from pathlib import Path

# Cada Tesseract usa uma linha de execução só. Sem isso, cada um tenta usar todos os núcleos (OpenMP) e,
# com várias conversões ao mesmo tempo (padrão: 4), eles se atropelam e quase param — páginas de 2 s
# levavam 30 min (achado no teste público de 27/11/2026). As conversões em paralelo já usam os núcleos.
os.environ.setdefault("OMP_THREAD_LIMIT", "1")
TESS_TIMEOUT = 180       # segundos por página: uma imagem patológica não trava o lote inteiro



class OcrTimeout(RuntimeError):
    """O Tesseract passou do tempo numa imagem (a página fica sem texto, com aviso)."""


OCR_BACKENDS = [("auto", "Automático"), ("tesseract", tr("Tesseract (mantém acentos)")),
                ("rapidocr", tr("RapidOCR (sem instalação, perde acentos)"))]


def _bundle_dirs() -> list[Path]:
    dirs = []
    if getattr(sys, "frozen", False):
        dirs.append(Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent)))
        dirs.append(Path(sys.executable).parent)
    dirs.append(Path(__file__).resolve().parent.parent)
    return dirs


@lru_cache(maxsize=1)
def tesseract_cmd() -> str | None:
    """Caminho do executável do Tesseract (embutido, no PATH ou no local padrão do Windows)."""
    exe = "tesseract.exe" if os.name == "nt" else "tesseract"
    candidates = [d / "tesseract" / exe for d in _bundle_dirs()]
    found = shutil.which("tesseract")
    if found:
        candidates.append(Path(found))
    if os.name == "nt":
        for env in ("ProgramFiles", "ProgramFiles(x86)", "LOCALAPPDATA"):
            base = os.environ.get(env)
            if base:
                candidates.append(Path(base) / "Tesseract-OCR" / exe)
                candidates.append(Path(base) / "Programs" / "Tesseract-OCR" / exe)
    for c in candidates:
        if c.is_file():
            tessdata = c.parent / "tessdata"
            if tessdata.is_dir() and "TESSDATA_PREFIX" not in os.environ:
                os.environ["TESSDATA_PREFIX"] = str(tessdata)
            return str(c)
    return None


@lru_cache(maxsize=1)
def tessdata_best_dir() -> str | None:
    """Pasta com os modelos "best" (mais precisos e mais lentos), se instalada.

    Vem no instalador do Windows (PADRÃO/COMPLETA) em ``tesseract/tessdata_best``; em outros
    sistemas pode ser indicada pela variável MARKINHO_TESSDATA_BEST."""
    env = os.environ.get("MARKINHO_TESSDATA_BEST")
    cands = ([Path(env)] if env else []) + [d / "tesseract" / "tessdata_best" for d in _bundle_dirs()]
    for c in cands:
        if c.is_dir() and any(c.glob("*.traineddata")):
            return str(c)
    return None


@lru_cache(maxsize=1)
def _has_osd() -> bool:
    cmd = tesseract_cmd()
    if not cmd:
        return False
    try:
        import pytesseract

        pytesseract.pytesseract.tesseract_cmd = cmd
        return "osd" in pytesseract.get_languages(config="")
    except Exception:  # noqa: BLE001
        return False


@lru_cache(maxsize=1)
def tesseract_languages() -> tuple[str, ...]:
    cmd = tesseract_cmd()
    if not cmd:
        return ()
    try:
        import pytesseract

        pytesseract.pytesseract.tesseract_cmd = cmd
        return tuple(sorted(set(pytesseract.get_languages(config="")) - {"osd"}))
    except Exception:  # noqa: BLE001
        return ()


def _has_module(name: str) -> bool:
    import importlib.util

    try:
        return importlib.util.find_spec(name) is not None
    except (ImportError, ValueError):
        return False


def available_backends() -> list[str]:
    out = []
    if tesseract_cmd() and _has_module("pytesseract"):
        out.append("tesseract")
    if _has_module("rapidocr_onnxruntime") or _has_module("rapidocr"):
        out.append("rapidocr")
    return out


def describe_status() -> str:
    av = available_backends()
    if not av:
        from .edition import upgrade_hint

        return upgrade_hint("ocr") or (tr("Nenhum OCR instalado. Instale o Tesseract (com o idioma português) ou "
                                       "`pip install rapidocr_onnxruntime`."))
    parts = []
    if "tesseract" in av:
        langs = tesseract_languages()
        parts.append("Tesseract (" + (", ".join(langs) if langs else "idiomas?") + ")")
    if "rapidocr" in av:
        parts.append("RapidOCR")
    return tr("OCR disponível: ") + "; ".join(parts)


def pick_backend(choice: str = "auto") -> str | None:
    av = available_backends()
    if choice in av:
        return choice
    return av[0] if av and choice == "auto" else None


def _tess_lang(lang: str) -> str:
    """Usa só os idiomas pedidos que estão instalados (evita erro do Tesseract)."""
    have = set(tesseract_languages())
    want = [x for x in lang.replace(",", "+").split("+") if x.strip()]
    ok = [x for x in want if x in have] or (["por"] if "por" in have else ["eng"] if "eng" in have else [])
    return "+".join(ok) or "eng"


@lru_cache(maxsize=1)
def _rapid():
    try:
        from rapidocr_onnxruntime import RapidOCR
    except ImportError:
        from rapidocr import RapidOCR  # type: ignore
    return RapidOCR()


def skew_angle(gray, limit: float = 5.0, step: float = 0.5) -> float:
    """Inclinação (graus) de uma página escaneada torta, só com o Pillow.

    Gira uma cópia reduzida e fica com o ângulo em que as linhas de texto ficam mais
    "nítidas" na projeção horizontal (variação entre linhas vizinhas)."""
    from PIL import Image

    small = gray.convert("L")
    small.thumbnail((900, 900))
    ink = small.point(lambda v: 255 if v < 140 else 0)       # texto branco sobre preto
    if not ink.getbbox():
        return 0.0

    def score(angle: float) -> float:
        r = ink.rotate(angle, resample=Image.BILINEAR, fillcolor=0)
        col = r.resize((1, r.height), Image.BOX)
        prof = list(col.get_flattened_data() if hasattr(col, "get_flattened_data") else col.getdata())
        return sum((prof[i + 1] - prof[i]) ** 2 for i in range(len(prof) - 1))

    n = int(limit / step)
    base = score(0.0)
    best_a, best_s = 0.0, base
    for k in range(-n, n + 1):
        a = k * step
        if a:
            sc = score(a)
            if sc > best_s:
                best_a, best_s = a, sc
    # só endireita quando a melhora é clara (evita girar páginas já retas por ruído)
    return best_a if best_s > base * 1.05 else 0.0


def enhance(img):
    """Prepara a imagem para o OCR: tons de cinza, contraste automático e página endireitada.

    Ajuda em fotos de celular e cópias escuras, desbotadas ou tortas; o tamanho não muda, então
    as posições das linhas continuam valendo."""
    from PIL import Image, ImageOps

    gray = ImageOps.autocontrast(img.convert("L"), cutoff=1)
    angle = skew_angle(gray)
    if angle:
        gray = gray.rotate(angle, resample=Image.BICUBIC, fillcolor=255)
    return gray


def _tessdata_arg(folder: str) -> str:
    """`--tessdata-dir` sem aspas: no Windows o pytesseract mantém as aspas como parte do caminho
    (“Error opening data file "C:\\…\\tessdata_best"/por.traineddata”). Caminho com espaço usa o
    nome curto do Windows (ex.: C:\\PROGRA~1\\…), que não tem espaços."""
    if os.name == "nt":
        if " " in folder:
            try:
                import ctypes

                buf = ctypes.create_unicode_buffer(1024)
                if ctypes.windll.kernel32.GetShortPathNameW(folder, buf, 1024):
                    folder = buf.value
            except Exception:  # noqa: BLE001
                pass
        return f"--tessdata-dir {folder}"
    import shlex

    return f"--tessdata-dir {shlex.quote(folder)}"


def _option(key: str, default):
    try:
        from .core import option

        return option(key, default)
    except Exception:  # noqa: BLE001
        return default


def _tess_data(img, lang: str, config: str):
    import pytesseract

    try:
        data = pytesseract.image_to_data(img, lang=lang, config=config, output_type=pytesseract.Output.DICT,
                                         timeout=TESS_TIMEOUT)
    except RuntimeError as exc:                   # o pytesseract avisa o tempo esgotado com RuntimeError
        if "timeout" not in str(exc).lower():
            raise
        raise OcrTimeout(tr("O OCR demorou mais de {0} s numa página e foi interrompido.").format(TESS_TIMEOUT)) from exc
    confs = [float(c) for w, c in zip(data["text"], data["conf"]) if w.strip() and float(c) >= 0]
    return data, (sum(confs) / len(confs) if confs else 0.0)


def ocr_lines(img, backend: str = "auto", lang: str = "por+eng", enhance_img: bool | None = None,
              model: str | None = None) -> list[dict]:
    """Reconhece o texto de uma imagem PIL. Devolve linhas com text, x0, x1, top, bottom
    e height, em pixels da imagem.

    ``enhance_img`` (opção ``ocr_enhance``) trata a imagem antes; ``model`` (opção ``ocr_model``)
    escolhe ``fast`` ou ``best`` (modelos mais precisos, se instalados)."""
    be = pick_backend(backend)
    if be is None:
        raise RuntimeError(describe_status())
    if img.mode not in ("RGB", "L"):
        img = img.convert("RGB")
    if be == "tesseract":
        import pytesseract

        pytesseract.pytesseract.tesseract_cmd = tesseract_cmd()
        if enhance_img is None:
            enhance_img = bool(_option("ocr_enhance", True))
        if model is None:
            model = str(_option("ocr_model", "fast"))
        if enhance_img:
            img = enhance(img)
        config = "--psm 3"
        best = tessdata_best_dir() if model == "best" else None
        tl = _tess_lang(lang)
        if best:
            have = {f.stem for f in Path(best).glob("*.traineddata")}
            if all(x in have for x in tl.split("+")):
                config += " " + _tessdata_arg(best)
        try:
            data, conf = _tess_data(img, tl, config)
        except Exception:  # noqa: BLE001 — modelos “best” com problema: usa os normais em vez de falhar
            if "--tessdata-dir" not in config:
                raise
            config = "--psm 3"
            data, conf = _tess_data(img, tl, config)
        # página de lado ou de cabeça para baixo: leitura ruim → detecta a orientação e refaz
        if enhance_img and conf < 60 and _has_osd():
            try:
                osd = pytesseract.image_to_osd(img, output_type=pytesseract.Output.DICT)
                rot = int(osd.get("rotate", 0))
            except Exception:  # noqa: BLE001
                rot = 0
            if rot:
                turned = img.rotate(-rot, expand=True)
                data2, conf2 = _tess_data(turned, tl, config)
                if conf2 > conf:
                    data = data2
        groups: dict[tuple, list[int]] = {}
        for i, word in enumerate(data["text"]):
            if not word.strip() or float(data["conf"][i]) < 0:
                continue
            key = (data["block_num"][i], data["par_num"][i], data["line_num"][i])
            groups.setdefault(key, []).append(i)
        lines = []
        for idxs in groups.values():
            x0 = min(data["left"][i] for i in idxs)
            x1 = max(data["left"][i] + data["width"][i] for i in idxs)
            top = min(data["top"][i] for i in idxs)
            bottom = max(data["top"][i] + data["height"][i] for i in idxs)
            # altura típica das palavras (ignora letras como "g" e "j" esticando a caixa)
            heights = sorted(data["height"][i] for i in idxs)
            confs = [float(data["conf"][i]) for i in idxs]
            lines.append({"text": " ".join(data["text"][i] for i in idxs), "x0": x0, "x1": x1,
                          "top": top, "bottom": bottom, "height": heights[len(heights) // 2],
                          "conf": sum(confs) / len(confs), "chars": sum(len(data["text"][i]) for i in idxs)})
        return lines
    import numpy as np

    result = _rapid()(np.array(img.convert("RGB")))
    if isinstance(result, tuple):          # rapidocr_onnxruntime: (resultado, tempos)
        items = result[0] or []
    else:                                  # rapidocr >= 2: objeto com boxes/txts/scores
        items = list(zip(result.boxes, result.txts, result.scores)) if result.txts else []
    lines = []
    for box, text, conf in items:
        xs = [p[0] for p in box]
        ys = [p[1] for p in box]
        lines.append({"text": text, "x0": min(xs), "x1": max(xs), "top": min(ys), "bottom": max(ys),
                      "height": max(ys) - min(ys), "conf": float(conf) * 100 if float(conf) <= 1 else float(conf),
                      "chars": len(text)})
    return lines


def ocr_words(img, backend: str = "auto", lang: str = "por+eng") -> list[dict]:
    """Palavras com posição (para ler a imagem como tabela). RapidOCR devolve trechos em vez de palavras."""
    be = pick_backend(backend)
    if be is None:
        raise RuntimeError(describe_status())
    if img.mode not in ("RGB", "L"):
        img = img.convert("RGB")
    if be != "tesseract":
        return ocr_lines(img, backend, lang)
    import pytesseract

    pytesseract.pytesseract.tesseract_cmd = tesseract_cmd()
    if _option("ocr_enhance", True):
        img = enhance(img)
    data, _conf = _tess_data(img, _tess_lang(lang), "--psm 6")
    out = []
    for i, w in enumerate(data["text"]):
        if w.strip() and float(data["conf"][i]) >= 0:
            out.append({"text": w, "x0": data["left"][i], "x1": data["left"][i] + data["width"][i],
                        "top": data["top"][i], "bottom": data["top"][i] + data["height"][i],
                        "height": data["height"][i]})
    return out


def words_to_table(words: list[dict]) -> list[list[str]]:
    """Agrupa palavras em linhas (pela altura) e colunas (pelos espaços grandes, alinhados entre linhas)."""
    if not words:
        return []
    hs = sorted(max(1, w["bottom"] - w["top"]) for w in words)
    h = hs[len(hs) // 2]
    rows: list[list[dict]] = []
    for w in sorted(words, key=lambda w: (w["top"] + w["bottom"]) / 2):
        cy = (w["top"] + w["bottom"]) / 2
        if rows and abs(cy - rows[-1][0]["_cy"]) <= h * 0.6:
            rows[-1].append(w)
        else:
            w = dict(w)
            rows.append([w])
        rows[-1][0].setdefault("_cy", cy)
    cells_by_row = []
    for r in rows:
        r.sort(key=lambda w: w["x0"])
        cells, cur = [], [r[0]]
        for w in r[1:]:
            if w["x0"] - cur[-1]["x1"] > h * 1.2:          # espaço grande: nova célula
                cells.append(cur)
                cur = [w]
            else:
                cur.append(w)
        cells.append(cur)
        cells_by_row.append([(c[0]["x0"], " ".join(x["text"] for x in c)) for c in cells])
    starts = sorted(x for row in cells_by_row for x, _ in row)
    anchors: list[float] = []
    for x in starts:                                         # início das colunas, alinhado entre linhas
        if not anchors or x - anchors[-1] > h * 2:
            anchors.append(x)
    table = []
    for row in cells_by_row:
        line = [""] * len(anchors)
        for x, text in row:
            k = max(i for i, a in enumerate(anchors) if a <= x + h * 2)
            line[k] = (line[k] + " " + text).strip()
        table.append(line)
    return table


def ocr_code(img, backend: str = "auto", lang: str = "por+eng") -> str:
    """Texto mantendo espaços e quebras de linha (código, terminal)."""
    be = pick_backend(backend)
    if be is None:
        raise RuntimeError(describe_status())
    if be != "tesseract":
        return "\n".join(ln["text"] for ln in sorted(ocr_lines(img, backend, lang), key=lambda ln: ln["top"]))
    import pytesseract

    pytesseract.pytesseract.tesseract_cmd = tesseract_cmd()
    if img.mode not in ("RGB", "L"):
        img = img.convert("RGB")
    data, _conf = _tess_data(img, _tess_lang(lang), "--psm 6 -c preserve_interword_spaces=1")
    words = [i for i, w in enumerate(data["text"]) if w.strip() and float(data["conf"][i]) >= 0]
    if not words:
        return ""
    # passo de um caractere (fonte de código é monoespaçada): cada palavra vai para a sua coluna
    long_words = [i for i in words if len(data["text"][i]) >= 3] or words
    cw = sorted(data["width"][i] / max(0.65, len(data["text"][i]) - 0.35)
                for i in long_words)[len(long_words) // 2] or 1
    groups: dict[tuple, list[int]] = {}
    for i in words:
        groups.setdefault((data["block_num"][i], data["par_num"][i], data["line_num"][i]), []).append(i)
    lines = sorted(groups.values(), key=lambda ix: min(data["top"][i] for i in ix))
    left = min(data["left"][i] for i in words)
    hs = sorted(data["height"][i] for i in words)
    lh = hs[len(hs) // 2] or 1
    out, prev_bottom = [], None
    for ix in lines:
        ix.sort(key=lambda i: data["left"][i])
        top = min(data["top"][i] for i in ix)
        if prev_bottom is not None and top - prev_bottom > lh * 1.2:
            out.append("")                                   # linha em branco entre blocos
        text = ""
        for i in ix:
            col = max(0, round((data["left"][i] - left) / cw))
            text += " " * max(1 if text else 0, col - len(text)) + data["text"][i]
        out.append(text.rstrip())
        prev_bottom = max(data["top"][i] + data["height"][i] for i in ix)
    return "\n".join(out)


def ocr_segments(img, backend: str = "auto", lang: str = "por+eng", scale: float = 1.0) -> list[dict]:
    """Linhas do OCR no formato de "segmento" do montador de PDF (coordenadas em pontos)."""
    segs = []
    for ln in ocr_lines(img, backend, lang):
        segs.append({"kind": "line", "text": ln["text"], "x0": ln["x0"] * scale, "x1": ln["x1"] * scale,
                     "top": ln["top"] * scale, "bottom": ln["bottom"] * scale,
                     # tamanho da fonte ~ altura da caixa da linha
                     "size": round(max(ln["height"] * scale * 0.95, 1), 1), "bold": False, "mono": False,
                     "conf": ln.get("conf", 100.0), "chars": ln.get("chars", len(ln["text"]))})
    return segs


def mean_confidence(segs: list[dict]) -> float | None:
    """Confiança média do OCR (0–100), ponderada pelo número de letras de cada linha."""
    total = sum(s.get("chars", 0) for s in segs if "conf" in s)
    if not total:
        return None
    return sum(s["conf"] * s.get("chars", 0) for s in segs if "conf" in s) / total
