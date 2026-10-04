"""Reversible masking of protected spans in one JATS paragraph-like element.

`mask()` turns an element into model-facing text where everything that must survive
translation untouched (variables, citations, figure refs, links, formulas, sub/sup,
species and software names) is replaced by a placeholder ⟦<T><n>⟧. `unmask()` puts the
Markdown rendering of each span back. Both modes share one renderer, so
`unmask(*mask(el)) == to_markdown(el)` holds by construction.

Placeholder types: V variable, N protected name, C citation group, F figure/media/table
reference, R section reference, L link, U sub/sup, M formula.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import xml.etree.ElementTree as ET

PH_OPEN, PH_CLOSE = "⟦", "⟧"
PH_RE = re.compile(rf"{PH_OPEN}[A-Z]\d+{PH_CLOSE}")
XLINK_HREF = "{http://www.w3.org/1999/xlink}href"
SKIP_TAGS = {"fig", "supplementary-material", "table-wrap"}  # extracted as own units
SPECIES_RE = re.compile(r"[A-Z][a-z]+(?: [a-z]+){0,2}\.?")
CITE_SEP_RE = re.compile(r"[,;–\-\u2009 ]*")
WS_RE = re.compile(r"[ \t\r\n]+")
TEX_RE = re.compile(r"\$\$(.*?)\$\$|\$(.*?)\$", re.DOTALL)
FORMULA_GAP_RE = re.compile(r" *(\n\n\$\$.*?\$\$\n\n) *", re.DOTALL)


class PlaceholderError(ValueError):
    pass


def ph(kind: str, n: int) -> str:
    return f"{PH_OPEN}{kind}{n}{PH_CLOSE}"


def _protected_re(protected: dict) -> re.Pattern | None:
    terms = sorted(protected.get("terms", []), key=len, reverse=True)
    alts = [re.escape(t) for t in terms] + list(protected.get("patterns", []))
    if not alts:
        return None
    return re.compile(r"(?<!\w)(?:" + "|".join(alts) + r")(?!\w)")


class _Ctx:
    def __init__(self, protected: dict, *, masking: bool):
        self.masking = masking
        self.protected = _protected_re(protected)
        self.spans: dict[str, dict] = {}
        self.counters: dict[str, int] = {}

    def atom(self, kind: str, md: str, **extra) -> str:
        if not self.masking:
            return md
        self.counters[kind] = self.counters.get(kind, 0) + 1
        key = ph(kind, self.counters[kind])
        self.spans[key] = {"type": kind, "md": md, **extra}
        return key


def _norm(s: str) -> str:
    return WS_RE.sub(" ", s)


def _clean_url(url: str) -> str:
    """PMC artifact: Springer wraps some URLs in <...>, leaving '>' / '%3e' at the end."""
    return re.sub(r"(?:%3e|>)+$", "", url.strip(), flags=re.IGNORECASE)


def _plain_text(ctx: _Ctx, text: str) -> str:
    text = _norm(text)
    if ctx.protected is None:
        return text
    out, pos = [], 0
    for m in ctx.protected.finditer(text):
        out += [text[pos : m.start()], ctx.atom("N", m.group())]
        pos = m.end()
    out.append(text[pos:])
    return "".join(out)


def _tex(el: ET.Element) -> tuple[str, bool]:
    tex = next(el.iter("tex-math"), None)
    raw = "".join(tex.itertext()) if tex is not None else ""
    m = TEX_RE.search(raw)
    if m:
        return (m.group(1) or m.group(2)).strip(), True
    return _norm("".join(el.itertext())).strip(), False


def _formula_md(el: ET.Element) -> str:
    body, is_tex = _tex(el)
    display = el.tag == "disp-formula"
    if not is_tex:
        return f"\n\n```\n{body}\n```\n\n" if display else f"`{body}`"
    return f"\n\n$${body}$$\n\n" if display else f"${body}$"


def _flat(el: ET.Element) -> list[tuple[str, object]]:
    nodes: list[tuple[str, object]] = []
    if el.text:
        nodes.append(("t", el.text))
    for ch in el:
        nodes.append(("e", ch))
        if ch.tail:
            nodes.append(("t", ch.tail))
    return nodes


def _is_bibr(node: tuple[str, object]) -> bool:
    return node[0] == "e" and node[1].tag == "xref" and node[1].get("ref-type") == "bibr"


def _citation_end(nodes: list, i: int) -> int | None:
    """If nodes[i:] is `bibr (sep bibr)* ]`, return the index of the closing text node."""
    j = i
    while j + 2 < len(nodes) and nodes[j + 1][0] == "t" and _is_bibr(nodes[j + 2]):
        sep = nodes[j + 1][1]
        if sep.startswith("]"):
            return j + 1
        if not CITE_SEP_RE.fullmatch(sep):
            return None
        j += 2
    if j + 1 < len(nodes) and nodes[j + 1][0] == "t" and nodes[j + 1][1].startswith("]"):
        return j + 1
    return None


def _citation_md(nodes: list) -> str:
    inner = "".join(_norm(v if k == "t" else "".join(v.itertext())) for k, v in nodes)
    return f"[{inner}]"


def _is_citation_sup(el: ET.Element) -> bool:
    nodes = _flat(el)
    if not nodes:
        return False
    saw_bibr = False
    for kind, val in nodes:
        if kind == "e":
            if not _is_bibr(("e", val)):
                return False
            saw_bibr = True
        elif not CITE_SEP_RE.fullmatch(val):
            return False
    return saw_bibr


def _render_children(el: ET.Element, ctx: _Ctx) -> str:
    nodes = _flat(el)
    out: list[str] = []
    i = 0
    while i < len(nodes):
        kind, val = nodes[i]
        if kind == "t":
            nxt_cite = i + 1 < len(nodes) and _is_bibr(nodes[i + 1]) and val.rstrip().endswith("[")
            end = _citation_end(nodes, i + 1) if nxt_cite else None
            if end is not None:
                before = val.rstrip()[:-1]
                out.append(_plain_text(ctx, before))
                out.append(ctx.atom("C", _citation_md(nodes[i + 1 : end])))
                nodes[end] = ("t", nodes[end][1][1:])
                i = end
                continue
            out.append(_plain_text(ctx, val))
        else:
            out.append(_render_element(val, ctx))
        i += 1
    return "".join(out)


def _render_element(el: ET.Element, ctx: _Ctx) -> str:
    tag = el.tag
    if tag in SKIP_TAGS:
        return ""
    if tag in {"disp-formula", "inline-formula"}:
        return ctx.atom("M", _formula_md(el))
    if tag == "sup" and _is_citation_sup(el):
        return ctx.atom("C", _citation_md(_flat(el)))
    if tag in {"sub", "sup"}:
        plain = _Ctx({}, masking=False)
        return ctx.atom("U", f"<{tag}>{_render_children(el, plain)}</{tag}>")
    if tag == "ext-link":
        text = _clean_url("".join(el.itertext()))
        href = _clean_url(el.get(XLINK_HREF, text))
        return ctx.atom("L", f"[{text}]({href})")
    if tag == "xref":
        text = _norm("".join(el.itertext()))
        if el.get("ref-type") == "sec":
            return ctx.atom("R", text, rid=el.get("rid"))
        if el.get("ref-type") == "bibr":
            return ctx.atom("C", f"[{text}]")
        return ctx.atom("F", text)
    if tag == "italic":
        text = "".join(el.itertext()).strip()
        if len(text) <= 3 and " " not in text:
            plain = _Ctx({}, masking=False)
            return ctx.atom("V", f"*{_render_children(el, plain)}*")
        if SPECIES_RE.fullmatch(text):
            return ctx.atom("N", f"*{text}*")
        return f"*{_render_children(el, ctx)}*"
    if tag == "bold":
        return f"**{_render_children(el, ctx)}**"
    if tag == "monospace":
        return ctx.atom("N", f"`{''.join(el.itertext())}`")
    return _render_children(el, ctx)


def _finish(md: str) -> str:
    return FORMULA_GAP_RE.sub(r"\1", md).strip()


def mask(el: ET.Element, protected: dict) -> tuple[str, dict]:
    """Return (model-facing text with placeholders, spans)."""
    ctx = _Ctx(protected, masking=True)
    return _finish(_render_children(el, ctx)), ctx.spans


def to_markdown(el: ET.Element, protected: dict) -> str:
    """Direct Markdown rendering of the source element (what unmask must reproduce)."""
    return _finish(_render_children(el, _Ctx(protected, masking=False)))


def unmask(text: str, spans: dict, titles: dict | None = None, *, strict: bool = True) -> str:
    """Replace placeholders by their Markdown; section refs use `titles[rid]` if given."""
    titles = titles or {}

    def repl(m: re.Match) -> str:
        span = spans.get(m.group())
        if span is None:
            if not strict:
                return m.group()
            raise PlaceholderError(f"unknown placeholder {m.group()}")
        if span["type"] == "R":
            return titles.get(span["rid"], span["md"])
        return span["md"]

    return _finish(PH_RE.sub(repl, text))


def check_placeholders(translated: str, source: str) -> None:
    """The multiset of placeholders must be identical (order may change)."""
    want, got = {}, {}
    for key in PH_RE.findall(source):
        want[key] = want.get(key, 0) + 1
    for key in PH_RE.findall(translated):
        got[key] = got.get(key, 0) + 1
    unknown = sorted(set(got) - set(want))
    if unknown:
        raise PlaceholderError(f"unknown placeholders: {' '.join(unknown)}")
    dup = sorted(k for k in got if got[k] > want[k])
    if dup:
        raise PlaceholderError(f"duplicated placeholders: {' '.join(dup)}")
    missing = sorted(k for k in want if k not in got or got[k] < want[k])
    if missing:
        raise PlaceholderError(f"missing placeholders: {' '.join(missing)}")
