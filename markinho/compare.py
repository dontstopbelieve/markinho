# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 dontstopbelieve — Markinho
"""Comparar duas versões de um documento (ex.: minuta e contrato final).

Compara pelo texto em Markdown: primeiro por parágrafos (o que entrou, saiu ou mudou), depois, dentro de
cada parágrafo alterado, palavra por palavra. Tudo local.
"""
from __future__ import annotations

import difflib
import html
import re
from dataclasses import dataclass, field

_MAX_BLOCKS = 20000          # documentos gigantes: limita o trabalho (a comparação continua útil)


@dataclass
class Change:
    kind: str                # "igual" | "novo" | "removido" | "alterado"
    old: str = ""
    new: str = ""


@dataclass
class Comparison:
    changes: list[Change] = field(default_factory=list)

    def count(self, kind: str) -> int:
        return sum(1 for c in self.changes if c.kind == kind)

    def summary(self) -> str:
        a, r, m = self.count("novo"), self.count("removido"), self.count("alterado")
        if not (a or r or m):
            return "As duas versões têm o mesmo texto."
        parts = []
        if m:
            parts.append(f"{m} trecho(s) alterado(s)")
        if a:
            parts.append(f"{a} trecho(s) novo(s)")
        if r:
            parts.append(f"{r} trecho(s) removido(s)")
        return ", ".join(parts) + "."


def _blocks(md: str) -> list[str]:
    from .postprocess import strip_frontmatter

    text = strip_frontmatter(md).replace("\r\n", "\n")
    text = re.sub(r"<!--[^\n]{0,500}-->", "", text)          # marcas de página e comentários
    out = [b.strip() for b in re.split(r"\n[ \t]*\n", text)]
    return [re.sub(r"[ \t]+", " ", b) for b in out if b][:_MAX_BLOCKS]


def compare(old_md: str, new_md: str) -> Comparison:
    a, b = _blocks(old_md), _blocks(new_md)
    sm = difflib.SequenceMatcher(None, a, b, autojunk=False)
    out = Comparison()
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "equal":
            out.changes += [Change("igual", x, x) for x in a[i1:i2]]
        elif tag == "insert":
            out.changes += [Change("novo", "", x) for x in b[j1:j2]]
        elif tag == "delete":
            out.changes += [Change("removido", x, "") for x in a[i1:i2]]
        else:                                                   # replace: emparelha os parecidos
            olds, news = a[i1:i2], b[j1:j2]
            for k in range(max(len(olds), len(news))):
                o = olds[k] if k < len(olds) else ""
                n = news[k] if k < len(news) else ""
                # parecidos = muitas palavras em comum; senão, um trecho saiu e outro entrou
                if o and n and difflib.SequenceMatcher(None, o.split(), n.split(), autojunk=False).ratio() >= 0.5:
                    out.changes.append(Change("alterado", o, n))
                else:
                    if o:
                        out.changes.append(Change("removido", o, ""))
                    if n:
                        out.changes.append(Change("novo", "", n))
    return out


def word_diff_html(old: str, new: str) -> str:
    """Um parágrafo alterado com <del> (saiu) e <ins> (entrou) palavra por palavra."""
    wa, wb = re.findall(r"\S+|\s+", old), re.findall(r"\S+|\s+", new)
    sm = difflib.SequenceMatcher(None, wa, wb, autojunk=False)
    out = []
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "equal":
            out.append(html.escape("".join(wa[i1:i2])))
        else:
            if i2 > i1:
                out.append(f"<del>{html.escape(''.join(wa[i1:i2]).strip())}</del>")
            if i2 > i1 and j2 > j1:
                out.append(" ")                                  # separa o que saiu do que entrou
            if j2 > j1:
                out.append(f"<ins>{html.escape(''.join(wb[j1:j2]).strip())}</ins>")
            nxt = wa[i2] if i2 < len(wa) else ""
            if nxt and not nxt.isspace() and (j2 > j1 or i2 > i1) and out and not out[-1].endswith(" "):
                out.append(" ")
    return "".join(out)


CSS = ("body{font-family:sans-serif;line-height:1.5} del{background:#ffd7d5;color:#000;text-decoration:"
       "line-through} ins{background:#ccf0d4;color:#000;text-decoration:none} .blk{margin:8px 0;padding:6px 10px;"
       "border-left:4px solid #ccc;white-space:pre-wrap} .novo{border-color:#2e7d32;background:#f1faf2}"
       " .removido{border-color:#c62828;background:#fdf1f1} .alterado{border-color:#f9a825} .tag{font-size:11px;"
       "color:#555;font-weight:bold} .igual{color:#666;border-color:#eee}")


def to_html(comp: Comparison, name_a: str = "Versão antiga", name_b: str = "Versão nova",
            show_equal: bool = False, title: str = "Comparação de versões") -> str:
    """Relatório em HTML (usado na janela e para salvar)."""
    rows = [f"<h2>{html.escape(title)}</h2>",
            f"<p><b>Antiga:</b> {html.escape(name_a)}<br><b>Nova:</b> {html.escape(name_b)}</p>",
            f"<p><b>Resumo:</b> {html.escape(comp.summary())} "
            "<span style='background:#ffd7d5'>&nbsp;riscado = saiu&nbsp;</span> "
            "<span style='background:#ccf0d4'>&nbsp;verde = entrou&nbsp;</span></p><hr>"]
    for c in comp.changes:
        if c.kind == "igual":
            if show_equal:
                rows.append(f"<div class='blk igual'>{html.escape(c.new)}</div>")
            continue
        if c.kind == "alterado":
            body = word_diff_html(c.old, c.new)
        elif c.kind == "novo":
            body = f"<ins>{html.escape(c.new)}</ins>"
        else:
            body = f"<del>{html.escape(c.old)}</del>"
        label = {"alterado": "ALTERADO", "novo": "NOVO", "removido": "REMOVIDO"}[c.kind]
        rows.append(f"<div class='blk {c.kind}'><span class='tag'>{label}</span><br>{body}</div>")
    return f"<html><head><meta charset='utf-8'><style>{CSS}</style></head><body>{''.join(rows)}</body></html>"
