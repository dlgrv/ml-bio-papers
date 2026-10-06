"""Convert arXiv LaTeXML HTML (export.arxiv.org/html) into a JATS article.

Chrome (nav, license banners) is dropped. Citations, links, emphasis, typewriter
spans, figures, and the bibliography are mapped onto the tags `jats_digest` already
understands.
"""

from __future__ import annotations

import re
from html.parser import HTMLParser
from xml.etree.ElementTree import Element, SubElement, register_namespace, tostring

XLINK_NS = "http://www.w3.org/1999/xlink"
XLINK_HREF = f"{{{XLINK_NS}}}href"
register_namespace("xlink", XLINK_NS)

VOID = frozenset(
    [
        "area",
        "base",
        "br",
        "col",
        "embed",
        "hr",
        "img",
        "input",
        "link",
        "meta",
        "param",
        "source",
        "track",
        "wbr",
    ]
)
SKIP_TAGS = frozenset(["script", "style", "svg", "button"])
WS_RE = re.compile(r"[ \t\r\n]+")


class _Node:
    __slots__ = ("attrs", "children", "tag")

    def __init__(self, tag: str, attrs: dict[str, str]):
        self.tag = tag
        self.attrs = attrs
        self.children: list[_Node | str] = []


class _Parser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.root = _Node("root", {})
        self.stack = [self.root]

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        ad = {k: (v or "") for k, v in attrs if k}
        node = _Node(tag, ad)
        self.stack[-1].children.append(node)
        if tag not in VOID:
            self.stack.append(node)

    def handle_endtag(self, tag: str) -> None:
        for i in range(len(self.stack) - 1, 0, -1):
            if self.stack[i].tag == tag:
                del self.stack[i:]
                return

    def handle_data(self, data: str) -> None:
        if data:
            self.stack[-1].children.append(data)


def _classes(node: _Node) -> set[str]:
    return set((node.attrs.get("class") or "").split())


def _has(node: _Node, token: str) -> bool:
    return token in _classes(node)


def _walk(node: _Node):
    yield node
    for ch in node.children:
        if isinstance(ch, _Node):
            yield from _walk(ch)


def _find(node: _Node, *, cls: str | None = None, tag: str | None = None) -> _Node | None:
    for n in _walk(node):
        if cls is not None and not _has(n, cls):
            continue
        if tag is not None and n.tag != tag:
            continue
        if cls is None and tag is None:
            continue
        return n
    return None


def _find_article(root: _Node) -> _Node:
    found = _find(root, cls="ltx_document")
    if found is None:
        raise ValueError("not a LaTeXML article: no ltx_document")
    return found


def _text_of(node: _Node) -> str:
    parts: list[str] = []
    for ch in node.children:
        if isinstance(ch, str):
            parts.append(ch)
        elif ch.tag == "br":
            parts.append(" ")
        else:
            parts.append(_text_of(ch))
    return WS_RE.sub(" ", "".join(parts)).strip()


def _append_text(el: Element, text: str) -> None:
    if not text:
        return
    kids = list(el)
    if kids:
        kids[-1].tail = (kids[-1].tail or "") + text
    else:
        el.text = (el.text or "") + text


def _inline(src: _Node, dest: Element) -> None:
    if src.tag in SKIP_TAGS:
        return
    for ch in src.children:
        if isinstance(ch, str):
            _append_text(dest, ch.replace("\xa0", " "))
            continue
        cls = _classes(ch)
        if ch.tag == "br":
            _append_text(dest, " ")
        elif ch.tag == "a":
            href = ch.attrs.get("href") or ""
            if href.startswith("#bib"):
                el = SubElement(dest, "xref", {"ref-type": "bibr", "rid": href[1:]})
                _inline(ch, el)
            elif href.startswith("#"):
                rid = href[1:]
                kind = (
                    "fig"
                    if re.search(r"\.F\d", rid) or (rid.startswith("S") and ".F" in rid)
                    else "sec"
                )
                el = SubElement(dest, "xref", {"ref-type": kind, "rid": rid})
                _inline(ch, el)
            elif href.startswith(("http://", "https://")):
                el = SubElement(dest, "ext-link", {"ext-link-type": "uri", XLINK_HREF: href})
                _inline(ch, el)
            else:
                _inline(ch, dest)
        elif ch.tag == "cite":
            _inline(ch, dest)
        elif ch.tag in {"em", "i"} or "ltx_font_italic" in cls:
            el = SubElement(dest, "italic")
            _inline(ch, el)
        elif ch.tag in {"b", "strong"} or "ltx_font_bold" in cls:
            el = SubElement(dest, "bold")
            _inline(ch, el)
        elif ch.tag in {"code", "tt"} or "ltx_font_typewriter" in cls:
            el = SubElement(dest, "monospace")
            _inline(ch, el)
        elif ch.tag == "math" or "ltx_Math" in cls:
            display = ch.attrs.get("display") == "block" or "ltx_displayed_math" in cls
            tex = (ch.attrs.get("alttext") or _text_of(ch)).strip()
            el = SubElement(dest, "disp-formula" if display else "inline-formula")
            tm = SubElement(el, "tex-math")
            tm.text = f"$${tex}$$" if display else f"${tex}$"
        elif ch.tag == "span" and "ltx_tag" in cls:
            continue
        else:
            _inline(ch, dest)


def _para(src: _Node, parent: Element) -> None:
    p = SubElement(parent, "p")
    if src.attrs.get("id"):
        p.set("id", src.attrs["id"])
    _inline(src, p)


def _figure(src: _Node, parent: Element) -> None:
    fig = SubElement(parent, "fig")
    if src.attrs.get("id"):
        fig.set("id", src.attrs["id"])
    href = ""
    for ch in src.children:
        if isinstance(ch, _Node) and ch.tag in {"object", "img"}:
            href = ch.attrs.get("data") or ch.attrs.get("src") or href
    caption_src = next(
        (
            ch
            for ch in src.children
            if isinstance(ch, _Node) and (ch.tag == "figcaption" or _has(ch, "ltx_caption"))
        ),
        None,
    )
    if caption_src is not None:
        cap = SubElement(fig, "caption")
        p = SubElement(cap, "p")
        _inline(caption_src, p)
    if href:
        SubElement(fig, "graphic", {XLINK_HREF: href})


def _title_el(sec: Element, src: _Node | None) -> None:
    if src is None:
        return
    title = SubElement(sec, "title")
    _inline(src, title)
    if title.text:
        title.text = WS_RE.sub(" ", title.text).strip()


def _section_title(src: _Node) -> _Node | None:
    for ch in src.children:
        if isinstance(ch, _Node) and ch.tag in {"h1", "h2", "h3", "h4", "h5", "h6"}:
            return ch
        if isinstance(ch, _Node) and any(
            t in _classes(ch)
            for t in (
                "ltx_title_section",
                "ltx_title_subsection",
                "ltx_title_subsubsection",
                "ltx_title_appendix",
            )
        ):
            return ch
    return None


def _fill_container(src: _Node, dest: Element) -> None:
    for ch in src.children:
        if not isinstance(ch, _Node):
            continue
        cls = _classes(ch)
        if ch.tag in {"h1", "h2", "h3", "h4", "h5", "h6"}:
            continue
        if "ltx_bibliography" in cls:
            continue
        if ch.tag == "p" and "ltx_p" in cls:
            _para(ch, dest)
        elif "ltx_para" in cls:
            for p in ch.children:
                if isinstance(p, _Node) and p.tag == "p":
                    _para(p, dest)
        elif ch.tag == "figure" or "ltx_figure" in cls:
            _figure(ch, dest)
        elif ch.tag == "section" and (
            "ltx_subsection" in cls or "ltx_subsubsection" in cls or "ltx_section" in cls
        ):
            nested = SubElement(dest, "sec")
            if ch.attrs.get("id"):
                nested.set("id", ch.attrs["id"])
            _title_el(nested, _section_title(ch))
            _fill_container(ch, nested)
        elif ch.tag == "table" or "ltx_tabular" in cls:
            p = SubElement(dest, "p")
            p.text = _text_of(ch)


def _refs(src: _Node, back: Element) -> None:
    ref_list = SubElement(back, "ref-list")
    title = next(
        (ch for ch in src.children if isinstance(ch, _Node) and ch.tag in {"h1", "h2", "h3", "h4"}),
        None,
    )
    _title_el(ref_list, title)
    items: list[_Node] = []

    def collect(n: _Node) -> None:
        if n.tag == "li" and "ltx_bibitem" in _classes(n):
            items.append(n)
            return
        for ch in n.children:
            if isinstance(ch, _Node):
                collect(ch)

    collect(src)
    for item in items:
        ref = SubElement(ref_list, "ref")
        if item.attrs.get("id"):
            ref.set("id", item.attrs["id"])
        tag = next(
            (
                ch
                for ch in item.children
                if isinstance(ch, _Node) and "ltx_tag_bibitem" in _classes(ch)
            ),
            None,
        )
        if tag is not None:
            SubElement(ref, "label").text = _text_of(tag)
        cit = SubElement(ref, "mixed-citation")
        cit.text = _text_of(item)


def html_to_jats(html: str) -> str:
    parser = _Parser()
    parser.feed(html)
    parser.close()
    src = _find_article(parser.root)
    article = Element("article", {"article-type": "research-article"})
    front = SubElement(article, "front")
    meta = SubElement(front, "article-meta")
    title_group = SubElement(meta, "title-group")
    title_src = _find(src, cls="ltx_title_document")
    article_title = SubElement(title_group, "article-title")
    if title_src is not None:
        _inline(title_src, article_title)
        if article_title.text:
            article_title.text = WS_RE.sub(" ", article_title.text).strip()
    abstract_src = _find(src, cls="ltx_abstract")
    if abstract_src is not None:
        abstract = SubElement(meta, "abstract")
        if abstract_src.attrs.get("id"):
            abstract.set("id", abstract_src.attrs["id"])
        for ch in abstract_src.children:
            if isinstance(ch, _Node) and ch.tag == "p":
                _para(ch, abstract)
    body = SubElement(article, "body")
    back = SubElement(article, "back")
    for ch in src.children:
        if not isinstance(ch, _Node):
            continue
        cls = _classes(ch)
        if "ltx_bibliography" in cls:
            _refs(ch, back)
        elif ch.tag == "section" and ("ltx_section" in cls or "ltx_appendix" in cls):
            sec = SubElement(body, "sec")
            if ch.attrs.get("id"):
                sec.set("id", ch.attrs["id"])
            _title_el(sec, _section_title(ch))
            _fill_container(ch, sec)
        elif ch.tag == "p" and "ltx_p" in cls:
            _para(ch, body)
        elif "ltx_para" in cls:
            for p in ch.children:
                if isinstance(p, _Node) and p.tag == "p":
                    _para(p, body)
        elif ch.tag == "figure" or "ltx_figure" in cls:
            _figure(ch, body)
    if not list(back):
        article.remove(back)
    return tostring(article, encoding="unicode")
