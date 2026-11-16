# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 dontstopbelieve — Markinho
"""Correção de caracteres perdidos ou trocados.

Extratores de PDF, OCR e arquivos com codificação errada costumam produzir:

* mojibake: "Ã§Ã£o" no lugar de "ção" (UTF-8 lido como Latin-1/Windows-1252);
* acentos soltos: "Educa¸c˜ao" (PDFs gerados por LaTeX) ou acentos decompostos;
* ligaduras tipográficas: "ﬁ", "ﬂ" no lugar de "fi", "fl";
* glifos sem mapeamento: "(cid:123)" ou "�" (caracteres perdidos);
* caracteres invisíveis: hífen discricionário, espaço de largura zero, controles;
* palavras hifenizadas na quebra de linha: "pala-\\nvra";
* entidades HTML que sobraram: "&amp;", "&#233;".

Cada correção pode ser ligada ou desligada em `FixOptions`. `fix_text` devolve
o texto corrigido e um `FixReport` com o que foi alterado.
"""
from __future__ import annotations

import html
import re
import unicodedata
from dataclasses import dataclass, field, fields

# --------------------------------------------------------------------------- #
# Opções e relatório
# --------------------------------------------------------------------------- #
@dataclass
class FixOptions:
    mojibake: bool = True          # "Ã§Ã£o" -> "ção"
    accents: bool = True           # "Educa¸c˜ao" -> "Educação", NFD -> NFC
    ligatures: bool = True         # "ﬁ" -> "fi"
    invisibles: bool = True        # hífen discricionário, ZWSP, BOM, controles
    hyphenation: bool = True       # "pala-\nvra" -> "palavra"
    html_entities: bool = True     # "&amp;" -> "&"
    cid_glyphs: bool = True        # remove "(cid:123)"
    spaces: bool = True            # NBSP e espaços estranhos -> espaço comum
    quotes: bool = False           # “aspas curvas” -> "aspas retas"

    LABELS = {
        "mojibake": ("Codificação trocada (mojibake)", "Ex.: “AÃ§Ã£o” → “Ação”, “â€œ” → “"),
        "accents": ("Acentos soltos/decompostos", "Ex.: “Educa¸c˜ao” → “Educação” (comum em PDFs)"),
        "ligatures": ("Ligaduras tipográficas", "Ex.: “ﬁm” → “fim”, “ﬂor” → “flor”"),
        "invisibles": ("Caracteres invisíveis e de controle", "Hífen discricionário, espaço de largura zero, BOM"),
        "hyphenation": ("Hifenização em quebra de linha", "Ex.: “pala-⏎vra” → “palavra”"),
        "html_entities": ("Entidades HTML", "Ex.: “&amp;amp;” → “&”, “&amp;#233;” → “é”"),
        "cid_glyphs": ("Glifos sem mapeamento “(cid:N)”", "Remove marcas de caracteres que o PDF não informou"),
        "spaces": ("Espaços especiais", "Espaço não separável e similares → espaço comum"),
        "quotes": ("Aspas tipográficas → retas", "“ ” ‘ ’ → \" '  (desligado por padrão)"),
    }

    @classmethod
    def keys(cls) -> list[str]:
        return [f.name for f in fields(cls)]

    @classmethod
    def none(cls) -> "FixOptions":
        return cls(**{k: False for k in cls.keys()})

    def to_dict(self) -> dict[str, bool]:
        return {k: getattr(self, k) for k in self.keys()}


@dataclass
class FixReport:
    counts: dict[str, int] = field(default_factory=dict)
    examples: dict[str, list[tuple[str, str]]] = field(default_factory=dict)
    lost_chars: int = 0     # "�" que restaram (não dá para recuperar)
    cid_removed: int = 0

    @property
    def total(self) -> int:
        return sum(self.counts.values())

    def add(self, key: str, before: str, after: str, n: int = 1) -> None:
        self.counts[key] = self.counts.get(key, 0) + n
        ex = self.examples.setdefault(key, [])
        if len(ex) < 5 and (before, after) not in ex:
            ex.append((before, after))

    def warnings(self) -> list[str]:
        out = []
        if self.lost_chars:
            out.append(f"{self.lost_chars} caractere(s) “�” irrecuperáveis no texto. "
                       "O arquivo original perdeu essa informação; tente outro motor "
                       "(Docling ou Marker com OCR) para recuperar.")
        if self.cid_removed:
            out.append(f"{self.cid_removed} glifo(s) “(cid:N)” sem mapeamento foram removidos — "
                       "o PDF não informa o caractere real; um motor com OCR pode recuperá-los.")
        return out

    def to_markdown(self) -> str:
        if not self.total and not self.warnings():
            return "Nenhuma correção foi necessária. ✔"
        lines = [f"**{self.total} correção(ões) aplicada(s)**", ""]
        for key, n in sorted(self.counts.items(), key=lambda kv: -kv[1]):
            label = FixOptions.LABELS.get(key, (key, ""))[0]
            lines.append(f"- **{label}**: {n}")
            for before, after in self.examples.get(key, []):
                shown_after = f"`{_show(after)}`" if after else "_(removido)_"
                lines.append(f"    - `{_show(before)}` → {shown_after}")
        warns = self.warnings()
        if warns:
            lines += ["", "**Atenção**", ""] + [f"- ⚠ {w}" for w in warns]
        return "\n".join(lines)


def _show(s: str) -> str:
    s = s.replace("\n", "⏎").replace("`", "'")
    s = "".join(f"<U+{ord(c):04X}>" if unicodedata.category(c) in ("Cf", "Cc", "Zs") and c != " "
                else f"+◌{c}" if unicodedata.combining(c) else c for c in s)
    return s[:40]


# --------------------------------------------------------------------------- #
# Tabelas
# --------------------------------------------------------------------------- #
LIGATURES = {
    "ﬀ": "ff", "ﬁ": "fi", "ﬂ": "fl", "ﬃ": "ffi", "ﬄ": "ffl",
    "ﬅ": "st", "ﬆ": "st", "Ĳ": "IJ", "ĳ": "ij", "Ꜳ": "AA", "ꜳ": "aa",
}

INVISIBLES = {
    "­": "",   # soft hyphen
    "​": "",   # zero width space
    "‌": "",   # ZWNJ
    "‍": "",   # ZWJ
    "⁠": "",   # word joiner
    "﻿": "",   # BOM
    "᠎": "",   # mongolian vowel separator
}

SPACES = {c: " " for c in "              　"}

QUOTES = {"“": '"', "”": '"', "„": '"', "‘": "'", "’": "'", "‚": "'",
          "«": '"', "»": '"', "′": "'", "″": '"'}

# acentos "de espaçamento" -> acento combinante equivalente
SPACING_TO_COMBINING = {
    "´": "́", "ˊ": "́",  # ´ agudo
    "`": "̀", "ˋ": "̀",  # ` grave
    "ˆ": "̂", "^": "̂",  # ˆ circunflexo
    "˜": "̃", "~": "̃",  # ˜ til
    "¨": "̈",                      # ¨ trema
    "¸": "̧",                      # ¸ cedilha
}
# ASCII ` ^ ~ só são tratados quando é inequívoco (entre letras), para não estragar Markdown
_ASCII_ACCENTS = {"`", "^", "~"}

_CID_RE = re.compile(r"\(cid:\d+\)")
_ENTITY_RE = re.compile(r"&(?:#\d{2,7}|#x[0-9a-fA-F]{2,6}|[a-zA-Z][a-zA-Z0-9]{1,31});")
_HYPHEN_RE = re.compile(r"(\b[^\W\d_]{2,})-\n[ \t]*([^\W\d_]{2,}\b)", re.UNICODE)
_CONTROL_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
_FENCE_RE = re.compile(r"^(```|~~~)", re.MULTILINE)

# sequências típicas de UTF-8 interpretado como cp1252/latin-1
_MOJIBAKE_HINT = re.compile(r"[ÃÂâÅÆÐÑØ][\x80-\xbfŒœŠšŸŽžƒˆ˜–—‘-„†-•…‰‹›€™]")
_MOJIBAKE_RUN = re.compile(r"[\x80-ÿŒœŠšŸŽžƒˆ˜–—‘-„†-•…‰‹›€™]{2,}")


# --------------------------------------------------------------------------- #
# Correções individuais
# --------------------------------------------------------------------------- #
def _map_chars(text: str, table: dict[str, str], key: str, rep: FixReport) -> str:
    if not any(c in text for c in table):
        return text
    out = []
    for c in text:
        if c in table:
            rep.add(key, c, table[c])
            out.append(table[c])
        else:
            out.append(c)
    return "".join(out)


def _redecode(run: str) -> str | None:
    for enc in ("cp1252", "latin-1"):
        try:
            fixed = run.encode(enc).decode("utf-8")
        except (UnicodeEncodeError, UnicodeDecodeError):
            continue
        if fixed != run:
            return fixed
    return None


def fix_mojibake(text: str, rep: FixReport) -> str:
    if not _MOJIBAKE_HINT.search(text) and not re.search(r"[\x80-\x9f]", text):
        return text
    try:  # ftfy é o melhor que existe para isso, se estiver instalado
        import ftfy

        cfg = ftfy.TextFixerConfig(
            unescape_html=False, remove_terminal_escapes=False, fix_latin_ligatures=False,
            fix_character_width=False, uncurl_quotes=False, fix_line_breaks=False,
            remove_control_chars=False, normalization=None, explain=False,
        )
        out = []
        for line in text.split("\n"):
            fixed = ftfy.fix_text(line, cfg)
            if fixed != line:
                rep.add("mojibake", _diff_snippet(line, fixed)[0], _diff_snippet(line, fixed)[1])
            out.append(fixed)
        return "\n".join(out)
    except ImportError:
        pass

    def repl(m: re.Match) -> str:
        run = m.group(0)
        fixed = _redecode(run)
        if fixed is None:
            return run
        rep.add("mojibake", run, fixed)
        return fixed

    text = _MOJIBAKE_RUN.sub(repl, text)
    # caracteres de controle C1 isolados (0x80-0x9F) que na verdade eram cp1252
    def c1(m: re.Match) -> str:
        try:
            ch = m.group(0).encode("latin-1").decode("cp1252")
        except UnicodeDecodeError:
            return m.group(0)
        rep.add("mojibake", m.group(0), ch)
        return ch

    return re.sub(r"[\x80-\x9f]", c1, text)


def _diff_snippet(a: str, b: str) -> tuple[str, str]:
    i = 0
    while i < min(len(a), len(b)) and a[i] == b[i]:
        i += 1
    j = 0
    while j < min(len(a), len(b)) - i and a[-1 - j] == b[-1 - j]:
        j += 1
    s = max(0, i - 3)
    return a[s:len(a) - j + 3][:30], b[s:len(b) - j + 3][:30]


_VOWELS_N = set("aeiouAEIOUnNyYcC")


def fix_accents(text: str, rep: FixReport) -> str:
    """Junta acentos soltos à letra correta e normaliza para NFC."""
    if any(c in text for c in SPACING_TO_COMBINING if c not in _ASCII_ACCENTS):
        chars = list(text)
        out: list[str] = []
        i = 0
        n = len(chars)
        while i < n:
            c = chars[i]
            comb = SPACING_TO_COMBINING.get(c)
            if comb is None or c in _ASCII_ACCENTS:
                out.append(c)
                i += 1
                continue
            prev = out[-1] if out else ""
            # pula um espaço entre acento e letra ("informa´ cao")
            j = i + 1
            if j < n and chars[j] == " " and j + 1 < n and chars[j + 1].isalpha() and not prev.isalpha():
                j += 1
            nxt = chars[j] if j < n else ""
            if comb == "̧":  # cedilha vai depois da letra: "c¸"
                if prev in "cC":
                    new = unicodedata.normalize("NFC", prev + comb)
                    rep.add("accents", prev + c, new)
                    out[-1] = new
                    i += 1
                    continue
                if nxt in "cC":
                    new = unicodedata.normalize("NFC", nxt + comb)
                    rep.add("accents", c + nxt, new)
                    out.append(new)
                    i = j + 1
                    continue
            elif nxt and nxt in _VOWELS_N and unicodedata.normalize("NFC", nxt + comb) != nxt + comb:
                new = unicodedata.normalize("NFC", nxt + comb)
                rep.add("accents", c + nxt, new)
                out.append(new)
                i = j + 1
                continue
            elif prev and prev in _VOWELS_N and unicodedata.normalize("NFC", prev + comb) != prev + comb \
                    and not (nxt.isalpha()):
                new = unicodedata.normalize("NFC", prev + comb)
                rep.add("accents", prev + c, new)
                out[-1] = new
                i += 1
                continue
            out.append(c)
            i += 1
        text = "".join(out)
    # acentos combinantes (NFD) -> forma composta (NFC)
    nfc = unicodedata.normalize("NFC", text)
    if nfc != text:
        n = sum(1 for c in text if unicodedata.combining(c)) - sum(1 for c in nfc if unicodedata.combining(c))
        if n > 0:
            a, b = _diff_snippet(text, nfc)
            rep.add("accents", a, b, n)
        text = nfc
    return text


def fix_hyphenation(text: str, rep: FixReport) -> str:
    def repl(m: re.Match) -> str:
        a, b = m.group(1), m.group(2)
        if not b[0].islower():  # "Norte-\nAmericano" fica como está
            return m.group(0)
        rep.add("hyphenation", f"{a}-\n{b}", a + b)
        return a + b

    return _HYPHEN_RE.sub(repl, text)


def fix_entities(text: str, rep: FixReport) -> str:
    def repl(m: re.Match) -> str:
        ent = m.group(0)
        val = html.unescape(ent)
        if val == ent or val in "<>":  # "&lt;" vira "<" e quebraria HTML embutido no Markdown
            return ent
        rep.add("html_entities", ent, val)
        return val

    return _ENTITY_RE.sub(repl, text)


def fix_cid(text: str, rep: FixReport) -> str:
    found = _CID_RE.findall(text)
    if found:
        rep.cid_removed += len(found)
        for f in found[:5]:
            rep.add("cid_glyphs", f, "", 0)
        rep.counts["cid_glyphs"] = rep.counts.get("cid_glyphs", 0) + len(found)
        text = _CID_RE.sub("", text)
    return text


def fix_controls(text: str, rep: FixReport) -> str:
    text = _map_chars(text, INVISIBLES, "invisibles", rep)
    found = _CONTROL_RE.findall(text)
    if found:
        for c in found:
            rep.add("invisibles", c, "")
        text = _CONTROL_RE.sub("", text)
    return text


# --------------------------------------------------------------------------- #
# Pipeline
# --------------------------------------------------------------------------- #
def _split_code(text: str) -> list[tuple[bool, str]]:
    """Separa o Markdown em trechos (é_código, texto) para não mexer em blocos de código."""
    parts: list[tuple[bool, str]] = []
    pos = 0
    in_code = False
    fence = ""
    for m in re.finditer(r"^(`{3,}|~{3,}).*$", text, re.MULTILINE):
        mark = m.group(1)
        if not in_code:
            parts.append((False, text[pos:m.start()]))
            pos, in_code, fence = m.start(), True, mark
        elif mark.startswith(fence[0]) and len(mark) >= len(fence):
            parts.append((True, text[pos:m.end()]))
            pos, in_code = m.end(), False
    parts.append((in_code, text[pos:]))
    return [p for p in parts if p[1]]


def fix_text(text: str, options: FixOptions | None = None) -> tuple[str, FixReport]:
    """Aplica as correções habilitadas. Blocos de código só recebem as correções de codificação."""
    opts = options or FixOptions()
    rep = FixReport()
    # correções "de codificação": valem para o texto todo, inclusive código
    if opts.mojibake:
        text = fix_mojibake(text, rep)
    if opts.invisibles:
        text = fix_controls(text, rep)
    if opts.ligatures:
        text = _map_chars(text, LIGATURES, "ligatures", rep)

    out = []
    for is_code, chunk in _split_code(text):
        if is_code:
            out.append(chunk)
            continue
        if opts.cid_glyphs:
            chunk = fix_cid(chunk, rep)
        if opts.accents:
            chunk = fix_accents(chunk, rep)
        if opts.html_entities:
            chunk = fix_entities(chunk, rep)
        if opts.hyphenation:
            chunk = fix_hyphenation(chunk, rep)
        if opts.spaces:
            chunk = _map_chars(chunk, SPACES, "spaces", rep)
        if opts.quotes:
            chunk = _map_chars(chunk, QUOTES, "quotes", rep)
        out.append(chunk)
    text = "".join(out)
    rep.lost_chars = text.count("�")
    return text, rep
