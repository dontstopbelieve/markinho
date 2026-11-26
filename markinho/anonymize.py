# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 dontstopbelieve — Markinho
"""Anonimização do Markdown convertido: dados pessoais, lista de palavras, metadados e imagens.

Tudo roda no computador, só com regras (nenhum modelo de IA, nada vai para a internet).
Os números com dígito verificador (CPF, CNPJ, PIS, título de eleitor, cartão) só são trocados
quando o dígito confere, para não apagar números que não são documentos.

Segurança: as expressões abaixo têm tamanho limitado ({1,64} etc.) e não usam `.*?` seguido de
espaço/fechamento — texto preparado não consegue travar o programa (ver tests/test_anonymize.py).

Atenção: a anonimização automática nunca é 100%. Trocar nomes por [PESSOA 1] é pseudonimização;
o usuário deve revisar o resultado.
"""
from __future__ import annotations

import re
import unicodedata
from collections import Counter
from dataclasses import dataclass, field
from typing import Callable

DISCLAIMER = ("O Markinho não se responsabiliza por dados que deixarem de ser encontrados ou que forem trocados "
              "por engano. Cabe a você revisar o arquivo anonimizado antes de qualquer uso ou compartilhamento.")
LIST_HELP = ("Maiúsculas, minúsculas e acentos não fazem diferença: “joão”, “JOÃO” e “Joao” são iguais. "
             "Mas cada forma diferente precisa estar na lista: “João da Silva” não esconde “João”, "
             "“Sr. Silva” nem “J. Silva”. Escreva todas as variações, uma por linha (apelidos, sobrenome "
             "sozinho, siglas, plural, erros de digitação comuns). Para que variações virem o mesmo "
             "marcador, use “termo = substituto” (ex.: “João = [PESSOA A]”).")

# (id, rótulo na interface, marcador, ligado por padrão)
KINDS: list[tuple[str, str, str, bool]] = [
    ("cpf", "CPF", "CPF", True),
    ("cnpj", "CNPJ (inclui o novo CNPJ com letras)", "CNPJ", True),
    ("pis", "PIS/PASEP/NIS", "PIS", True),
    ("titulo", "Título de eleitor", "TÍTULO DE ELEITOR", True),
    ("rg", "RG e CNH (quando escritos “RG”/“CNH” antes do número)", "DOCUMENTO", True),
    ("cartao", "Cartão de crédito", "CARTÃO", True),
    ("email", "E-mail", "E-MAIL", True),
    ("telefone", "Telefone", "TELEFONE", True),
    ("cep", "CEP", "CEP", True),
    ("processo", "Número de processo (padrão do CNJ)", "PROCESSO", True),
    ("oab", "Registro na OAB", "OAB", True),
    ("placa", "Placa de veículo (quando escrita “placa” antes)", "PLACA", False),
    ("ip", "Endereço IP", "IP", False),
    ("assinatura", "Assinaturas eletrônicas (“Assinado eletronicamente por…”)", "PESSOA", True),
    ("nomes", "Nomes depois de Sr., Dra., réu, autor, paciente, nome:…", "PESSOA", True),
]
KIND_LABELS = {k: lbl for k, lbl, _, _ in KINDS}
MARKERS = {k: m for k, _, m, _ in KINDS}
DEFAULT_KINDS = [k for k, _, _, on in KINDS if on]

MODES = [
    ("marcador", "Marcador: [CPF], [E-MAIL], [PESSOA]"),
    ("pseudonimo", "Pseudônimo numerado: [PESSOA 1], [CPF 2] (o mesmo dado recebe sempre o mesmo número)"),
    ("mascara", "Máscara parcial: ***.456.789-**, j***@exemplo.com, J. S."),
]


@dataclass
class AnonOptions:
    kinds: list[str] = field(default_factory=lambda: list(DEFAULT_KINDS))
    mode: str = "pseudonimo"
    words: str = ""              # uma palavra/expressão por linha; "termo = substituto" é opcional
    metadata: bool = True        # tirar autor, datas, assunto e nome do arquivo do frontmatter
    image_metadata: bool = True  # tirar EXIF/GPS das imagens (sem perder qualidade)
    remove_images: bool = False  # não incluir imagens (fotos, assinaturas escaneadas)


@dataclass
class AnonReport:
    counts: Counter = field(default_factory=Counter)

    @property
    def total(self) -> int:
        return sum(self.counts.values())

    def summary(self) -> str:
        if not self.total:
            return "nenhum dado pessoal encontrado"
        names = {**{k: lbl.split(" (")[0] for k, lbl in KIND_LABELS.items()}, "lista": "Sua lista",
                 "nomes": "Nomes", "assinatura": "Assinaturas"}
        return " · ".join(f"{names.get(k, k)}: {n}" for k, n in self.counts.most_common())


# --------------------------------------------------------------------------- #
# Dígitos verificadores
# --------------------------------------------------------------------------- #
def _digits(s: str) -> str:
    return re.sub(r"\D", "", s)


def valid_cpf(s: str) -> bool:
    d = _digits(s)
    if len(d) != 11 or d == d[0] * 11:
        return False
    for n in (9, 10):
        total = sum(int(d[i]) * (n + 1 - i) for i in range(n))
        if (total * 10 % 11) % 10 != int(d[n]):
            return False
    return True


def valid_cnpj(s: str) -> bool:
    """CNPJ numérico ou alfanumérico (a partir de 2026: letras nas 12 primeiras posições)."""
    c = re.sub(r"[.\-/\s]", "", s.upper())
    if len(c) != 14 or not re.fullmatch(r"[0-9A-Z]{12}\d{2}", c) or c == c[0] * 14:
        return False
    vals = [ord(ch) - 48 for ch in c]
    for n in (12, 13):
        weights = list(range(n - 7, 1, -1)) + list(range(9, 1, -1))
        total = sum(v * w for v, w in zip(vals[:n], weights))
        dv = 0 if total % 11 < 2 else 11 - total % 11
        if dv != vals[n]:
            return False
    return True


def valid_pis(s: str) -> bool:
    d = _digits(s)
    if len(d) != 11 or d == d[0] * 11:
        return False
    total = sum(int(a) * w for a, w in zip(d[:10], (3, 2, 9, 8, 7, 6, 5, 4, 3, 2)))
    dv = 11 - total % 11
    return (0 if dv >= 10 else dv) == int(d[10])


def valid_titulo(s: str) -> bool:
    d = _digits(s)
    if len(d) != 12:
        return False
    uf = int(d[8:10])
    if not 1 <= uf <= 28:
        return False
    r1 = sum(int(a) * w for a, w in zip(d[:8], range(2, 10))) % 11
    dv1 = 0 if r1 == 10 else r1
    if uf in (1, 2) and r1 == 0:
        dv1 = 1
    r2 = (int(d[8]) * 7 + int(d[9]) * 8 + dv1 * 9) % 11
    dv2 = 0 if r2 == 10 else r2
    if uf in (1, 2) and r2 == 0:
        dv2 = 1
    return int(d[10]) == dv1 and int(d[11]) == dv2


def valid_luhn(s: str) -> bool:
    d = _digits(s)
    if not 13 <= len(d) <= 19:
        return False
    total = 0
    for i, ch in enumerate(reversed(d)):
        n = int(ch)
        if i % 2:
            n = n * 2 - 9 if n > 4 else n * 2
        total += n
    return total % 10 == 0


def _year_range(v: str) -> bool:
    """'2019-2020' no fim do número: é intervalo de anos, não telefone."""
    m = re.search(r"(\d{4})-(\d{4})$", v)
    return bool(m) and all(1900 <= int(x) <= 2100 for x in m.groups()) and not v.lstrip("(+").startswith("9")


# --------------------------------------------------------------------------- #
# Padrões (todos com tamanho limitado)
# --------------------------------------------------------------------------- #
_UP = "A-ZÀ-ÖØ-Þ"
_LOW = "a-zß-öø-ÿ"
_NAME_WORD = rf"[{_UP}][{_UP}{_LOW}'’]{{1,24}}"
_CONNECTOR = r"(?:d[aeo]s?|e|del|van|von|di)"
_NAME = rf"{_NAME_WORD}(?:[ \t]+(?:{_CONNECTOR}[ \t]+)?{_NAME_WORD}){{0,6}}"

_PATTERNS: list[tuple[str, re.Pattern, Callable[[str], bool] | None]] = [
    ("processo", re.compile(r"(?<![\d.])\d{7}-\d{2}\.\d{4}\.\d\.\d{2}\.\d{4}(?!\d|\.\d)"), None),
    ("email", re.compile(r"(?<![\w.+-])[\w.+-]{1,64}@[A-Za-z0-9-]{1,63}(?:\.[A-Za-z0-9-]{1,63}){1,6}"), None),
    ("cnpj", re.compile(r"(?<![\w./-])[0-9A-Z]{2}\.?[0-9A-Z]{3}\.?[0-9A-Z]{3}/?[0-9A-Z]{4}-?\d{2}(?![\w/-])"),
     valid_cnpj),
    ("cartao", re.compile(r"(?<![\d.-])\d{4}(?:[ -]?\d{4}){2}[ -]?\d{1,7}(?![\d-])"), valid_luhn),
    ("titulo", re.compile(r"(?<![\d.])\d{4}[ .]?\d{4}[ .]?\d{4}(?![\d.])"), valid_titulo),
    ("cpf", re.compile(r"(?<![\d./-])\d{3}\.?\d{3}\.?\d{3}-?\d{2}(?![\d/-])"), valid_cpf),
    ("pis", re.compile(r"(?<![\d./-])\d{3}\.?\d{5}\.?\d{2}-?\d(?![\d/-])"), valid_pis),
    ("telefone", re.compile(r"(?<![\w+(])(?:\+55[ \t]?\(?\d{2}\)?[ \t]?9?\d{4}[- \t]?\d{4}"
                            r"|\(\d{2}\)[ \t]?9?\d{4}[- \t]?\d{4}"
                            r"|\d{2}[ \t]9?\d{4}-\d{4}"
                            r"|9\d{4}-\d{4})(?![\d-])"), lambda v: not _year_range(v)),
    ("cep", re.compile(r"(?<![\d.-])\d{2}\.?\d{3}-\d{3}(?![\d-])|\bCEP[: \t]{1,3}(?P<v>\d{8})(?!\d)"), None),
    ("oab", re.compile(r"\bOAB[ \t]?/?[ \t]?[A-Z]{2}[ \t]?(?:n[º°o.]{1,2}[ \t]?)?\d{1,3}\.?\d{3}(?:-?[A-Z])?(?!\d)"
                       r"|\b\d{1,3}\.?\d{3}[ \t]?(?:-[ \t]?)?OAB[ \t]?/[ \t]?[A-Z]{2}\b"), None),
    ("rg", re.compile(r"\b(?:RG|CNH|R\.G\.)(?:[ \t]?(?:n[º°o.]{1,2}|:|-)){0,2}[ \t]{0,3}"
                      r"(?P<v>\d{1,2}\.?\d{3}\.?\d{3}(?:-?[\dXx]{1,2})?)(?![\d])"), None),
    ("placa", re.compile(r"\b[Pp]laca[: \t]{1,3}(?P<v>[A-Z]{3}-?\d[A-Z0-9]\d{2})\b"), None),
    ("ip", re.compile(r"(?<![\d.])(?:(?:25[0-5]|2[0-4]\d|1?\d?\d)\.){3}(?:25[0-5]|2[0-4]\d|1?\d?\d)(?![\d.])"), None),
]

_SIGNATURE = re.compile(r"(?i:assinad[oa]|firmad[oa])[ \t]+(?i:eletronicamente|digitalmente)[ \t]+(?i:por):?[ \t]*"
                        rf"(?P<name>{_NAME})")
_HINTS = (r"Sr|Sra|Srta|Dr|Dra|Prof|Profa|réu|ré|autora?|requerentes?|requerid[oa]|reclamante|reclamad[oa]|"
          r"paciente|advogad[oa]|testemunha|nome|cliente|contratante|contratad[oa]|interessad[oa]|"
          r"impetrante|exequente|executad[oa]|apelante|apelad[oa]|agravante|agravad[oa]|menor|"
          r"servidora?|funcionária?|empregad[oa]|aluna?|candidata?")
_NAMED = re.compile(rf"(?<![\w])(?i:{_HINTS})(?:\.|:|,)?[ \t]{{1,3}}(?P<name>{_NAME})")
_STOP = {"de", "da", "do", "das", "dos", "e", "o", "a", "os", "as", "que", "em", "no", "na", "por", "para",
         "presidente", "juiz", "juíza", "relator", "relatora", "doutor", "doutora", "senhor", "senhora",
         "ministério", "estado", "município", "união", "fazenda", "justiça", "tribunal", "público", "pública"}

# imagens e caminhos não podem ser alterados (o link quebraria)
# só o ENDEREÇO das imagens é protegido; o texto alternativo (descrição) também é anonimizado
_PROTECT = re.compile(r"(?P<alt>!\[[^\]\n]{0,500}\])\([^)\n]{0,2000}\)|\bsrc[ \t]*=[ \t]*\"[^\"\n]{0,2000}\"|\bsrc[ \t]*=[ \t]*'[^'\n]{0,2000}'"
                      r"|data:[\w/+.-]{1,40};base64,[A-Za-z0-9+/=]+")
# marcador que nenhuma regra consegue encontrar (caracteres de uso privado do Unicode, sem dígitos)
_MARK_OPEN, _MARK_CLOSE, _MARK_DIGIT0 = "\ue000", "\ue001", 0xE100
_MARK_RE = re.compile("\ue000([\ue100-\ue109]+)\ue001")
# depois de uma pista, um rótulo seguido de dois-pontos ("Nome Completo: João") não é o nome
_NAME_AFTER_COLON = re.compile(rf"[ \t]{{0,3}}:[ \t]{{0,3}}(?P<name>{_NAME})")


def _fold(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", s.lower()) if unicodedata.category(c) != "Mn")


class _Replacer:
    def __init__(self, opts: AnonOptions):
        self.opts = opts
        self.report = AnonReport()
        self.numbers: dict[tuple[str, str], int] = {}
        self.next: Counter = Counter()

    def token(self, kind: str, value: str, marker: str | None = None) -> str:
        self.report.counts[kind] += 1
        marker = marker or MARKERS.get(kind, "OCULTO")
        mode = self.opts.mode
        if mode == "mascara":
            return mask(kind, value)
        if mode == "pseudonimo":
            key = (marker, _fold(re.sub(r"[\s.\-/()]", "", value)) if kind != "nomes" else _fold(value))
            if key not in self.numbers:
                self.next[marker] += 1
                self.numbers[key] = self.next[marker]
            return f"[{marker} {self.numbers[key]}]"
        return f"[{marker}]"


def mask(kind: str, value: str) -> str:
    """Máscara parcial: mostra só parte do dado."""
    if kind == "email":
        user, _, dom = value.partition("@")
        return (user[:1] + "***@" + dom) if user else "***@" + dom
    if kind in ("nomes", "assinatura", "lista"):
        parts = [p for p in re.split(r"\s+", value) if p and p.lower() not in _STOP]
        return " ".join(p[0].upper() + "." for p in parts) or "***"
    out, digits = [], [i for i, ch in enumerate(value) if ch.isalnum()]
    keep = set(digits[3:-2]) if len(digits) > 6 else set()
    for i, ch in enumerate(value):
        out.append(ch if (not ch.isalnum() or i in keep) else "*")
    return "".join(out)


def _word_list(text: str) -> list[tuple[str, str | None]]:
    items: list[tuple[str, str | None]] = []
    for line in (text or "").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        term, sep, sub = line.partition("=")
        term = term.strip()
        if len(term) >= 2:
            items.append((term, sub.strip() if sep else None))
    return sorted(items, key=lambda t: -len(t[0]))


def _term_re(term: str) -> re.Pattern:
    """Termo da lista: sem diferenciar maiúsculas e acentos, palavra inteira."""
    parts = []
    for ch in term:
        base = _fold(ch)
        if ch.isspace():
            parts.append(r"[ \t]+")
        elif base.isalpha() and len(base) == 1:
            variants = {c for c in (ch, ch.lower(), ch.upper(), base, base.upper())}
            variants |= {c for c in "àáâãäåèéêëìíîïòóôõöùúûüçñ" if _fold(c) == base}
            variants |= {c.upper() for c in list(variants)}
            parts.append("[" + "".join(sorted(re.escape(v) for v in variants)) + "]")
        else:
            parts.append(re.escape(ch))
    return re.compile(r"(?<![\w])" + "".join(parts) + r"(?![\w])")


def anonymize(md: str, opts: AnonOptions) -> tuple[str, AnonReport]:
    """Troca dados pessoais do texto conforme `opts`. Devolve (texto, relatório)."""
    rep = _Replacer(opts)
    kinds = set(opts.kinds)

    # protege imagens/caminhos
    kept: list[str] = []

    def keep(m: re.Match) -> str:
        alt = m.group("alt") or ""              # o texto da imagem continua visível (e é anonimizado)
        kept.append(m.group(0)[len(alt):])
        n = "".join(chr(_MARK_DIGIT0 + int(d)) for d in str(len(kept) - 1))
        return f"{alt}{_MARK_OPEN}{n}{_MARK_CLOSE}"

    text = _PROTECT.sub(keep, md)

    # 1) lista do usuário (primeiro: o usuário sabe o que quer esconder)
    for i, (term, sub) in enumerate(_word_list(opts.words)):
        def repl_word(m: re.Match, sub=sub) -> str:
            if sub:
                rep.report.counts["lista"] += 1
                return sub
            return rep.token("lista", m.group(0), "NOME")
        text = _term_re(term).sub(repl_word, text)

    # 2) números e endereços
    for kind, pat, check in _PATTERNS:
        if kind not in kinds:
            continue

        def repl(m: re.Match, kind=kind, check=check) -> str:
            whole = m.group(0)
            g = "v" if "v" in m.re.groupindex and m.group("v") is not None else 0
            core = m.group(g)
            if check and not check(core):
                return whole
            a, b = m.start(g) - m.start(), m.end(g) - m.start()
            return whole[:a] + rep.token(kind, core) + whole[b:]
        text = pat.sub(repl, text)

    # 3) nomes: assinaturas e pistas ("réu Fulano"); cada nome encontrado é trocado no texto todo
    names: list[str] = []
    signed: set[str] = set()
    if "assinatura" in kinds:
        signed = {m.group("name") for m in _SIGNATURE.finditer(text)}
        names += list(signed)
    if "nomes" in kinds:
        for m in _NAMED.finditer(text):
            label = _NAME_AFTER_COLON.match(text, m.end())
            words = (label or m).group("name").split()
            while words and words[-1].lower() in _STOP:
                words.pop()
            if words and words[0].lower() not in _STOP and (len(words) >= 2 or len(words[0]) >= 4):
                names.append(" ".join(words))
    if opts.mode == "pseudonimo":               # numera na ordem em que aparecem no texto
        for name in sorted(set(names), key=lambda n: _fold(text).find(_fold(n))):
            key = ("PESSOA", _fold(name))
            if key not in rep.numbers:
                rep.next["PESSOA"] += 1
                rep.numbers[key] = rep.next["PESSOA"]
    for name in sorted(set(names), key=len, reverse=True):
        kind = "assinatura" if name in signed else "nomes"
        text = _term_re(name).sub(lambda m, kind=kind: rep.token(kind, m.group(0), "PESSOA"), text)

    text = _MARK_RE.sub(lambda m: kept[int("".join(str(ord(c) - _MARK_DIGIT0) for c in m.group(1)))], text)
    return text, rep.report


# --------------------------------------------------------------------------- #
# Metadados e imagens
# --------------------------------------------------------------------------- #
def strip_image_metadata(data: bytes) -> bytes:
    """Tira EXIF/GPS/XMP/comentários de JPEG e PNG sem recompactar (sem perder qualidade)."""
    try:
        if data[:2] == b"\xff\xd8":
            return _strip_jpeg(data)
        if data[:8] == b"\x89PNG\r\n\x1a\n":
            return _strip_png(data)
        if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
            return _strip_webp(data)
    except Exception:  # noqa: BLE001 - arquivo estranho: devolve como está
        pass
    return data


def _strip_jpeg(data: bytes) -> bytes:
    out = bytearray(data[:2])
    i = 2
    while i + 4 <= len(data):
        if data[i] != 0xFF:
            break
        marker = data[i + 1]
        if marker == 0xDA:                       # início da imagem: copia o resto
            out += data[i:]
            return bytes(out)
        size = int.from_bytes(data[i + 2:i + 4], "big")
        seg = data[i:i + 2 + size]
        # APP1 (EXIF/XMP), APP2..APP15 exceto ICC (APP2 "ICC_PROFILE"), COM (comentário)
        # APP14 "Adobe" é mantido: diz como ler as cores (sem ele, JPEG CMYK sai com cores trocadas)
        keep_seg = seg[4:15] == b"ICC_PROFILE" or (marker == 0xEE and seg[4:9] == b"Adobe")
        drop = marker == 0xFE or (0xE1 <= marker <= 0xEF and not keep_seg)
        if not drop:
            out += seg
        i += 2 + size
    return data


def _strip_png(data: bytes) -> bytes:
    out = bytearray(data[:8])
    i = 8
    while i + 12 <= len(data):
        n = int.from_bytes(data[i:i + 4], "big")
        kind = data[i + 4:i + 8]
        chunk = data[i:i + 12 + n]
        if kind not in (b"tEXt", b"iTXt", b"zTXt", b"eXIf", b"tIME"):
            out += chunk
        i += 12 + n
        if kind == b"IEND":
            return bytes(out)
    return data


def _strip_webp(data: bytes) -> bytes:
    out = bytearray()
    i = 12
    while i + 8 <= len(data):
        kind = data[i:i + 4]
        n = int.from_bytes(data[i + 4:i + 8], "little")
        chunk = data[i:i + 8 + n + (n & 1)]
        if kind not in (b"EXIF", b"XMP "):
            out += chunk
        i += 8 + n + (n & 1)
    body = b"WEBP" + bytes(out)
    if len(out) and data[12:16] == b"VP8X":     # avisa que não há mais EXIF/XMP
        flags = body[12] & ~0x0C
        body = body[:12] + bytes([flags]) + body[13:]
    return b"RIFF" + len(body).to_bytes(4, "little") + body


def clean_metadata(meta: dict) -> dict:
    """Só o que não identifica ninguém: número de páginas/slides/planilhas."""
    return {k: v for k, v in (meta or {}).items() if k in ("pages", "slides", "sheets")}


_PRIVATE_KEYS = {"author", "autor", "authors", "creator", "subject", "keywords", "created", "modified",
                 "source", "lastmodifiedby", "last_modified_by", "company", "manager", "date"}


def strip_frontmatter_private(md: str) -> str:
    """Num .md que já tem frontmatter (---), tira os campos que identificam pessoas ou o arquivo."""
    if not md.startswith("---\n"):
        return md
    end = md.find("\n---", 4)
    if end < 0:
        return md
    out, skipping = [], False
    for line in md[4:end].split("\n"):
        if line[:1] in (" ", "\t", "-") and skipping:
            continue
        key = line.split(":", 1)[0].strip().lower()
        skipping = ":" in line and key in _PRIVATE_KEYS
        if not skipping:
            out.append(line)
    if not any(line.strip() for line in out):
        return md[end + 4:].lstrip("\n")
    return "---\n" + "\n".join(out) + md[end:]
