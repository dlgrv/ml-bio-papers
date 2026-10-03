#!/usr/bin/env python3
"""Digest PMC JATS XML into ordered translation units (units.json).

One unit = one title / heading / paragraph / figure caption / supplementary caption /
reference. References are copied, not translated.

Usage: jats_digest.py <slug>   (reads translate/runs/<slug>/source.xml)
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import TYPE_CHECKING

from defusedxml.ElementTree import fromstring

from translate.lib import mask
from translate.lib.config import default_root
from translate.lib.paths import source_xml, work_dir

if TYPE_CHECKING:
    import xml.etree.ElementTree as ET

CONTAINERS = {"sec", "ack", "notes", "fn-group", "fn", "app", "app-group", "boxed-text"}
FIXED_RU = {"Abstract": "Аннотация", "References": "Список литературы"}
XLINK_HREF = "{http://www.w3.org/1999/xlink}href"


def _graphic_hrefs(fig: ET.Element) -> list[str]:
    hrefs: list[str] = []
    for tag in ("graphic", "inline-graphic"):
        for el in fig.iter(tag):
            href = (el.get(XLINK_HREF) or el.get("href") or "").strip()
            if href:
                hrefs.append(Path(href).name)
    return hrefs


def load_protected(root: str | None = None) -> dict:
    path = Path(root or default_root()) / "translate" / "rules" / "protected.json"
    return json.loads(path.read_text(encoding="utf-8"))


class _Digest:
    def __init__(self, protected: dict):
        self.protected = protected
        self.units: list[dict] = []

    def add(self, kind: str, **fields) -> dict:
        unit = {
            "id": f"u{len(self.units) + 1:03d}",
            "kind": kind,
            "level": None,
            "src_id": None,
            "translate": True,
            "text": "",
            "spans": {},
            "source_md": "",
            **fields,
        }
        self.units.append(unit)
        return unit

    def text_unit(self, kind: str, el: ET.Element, **fields) -> None:
        text, spans = mask.mask(el, self.protected)
        if not text:
            return
        md = mask.to_markdown(el, self.protected)
        self.add(kind, text=text, spans=spans, source_md=md, **fields)

    def heading(
        self, title: ET.Element | None, level: int, src_id: str | None, fixed: str | None = None
    ) -> None:
        if fixed is not None:
            self.add(
                "heading",
                level=level,
                src_id=src_id,
                translate=False,
                source_md=fixed,
                fixed_ru=FIXED_RU[fixed],
            )
        elif title is not None:
            self.text_unit("heading", title, level=level, src_id=src_id)

    def figure(self, fig: ET.Element) -> None:
        label = "".join(fig.findtext("label") or "").strip()
        caption = fig.find("caption")
        graphics = _graphic_hrefs(fig)
        if caption is not None:
            self.text_unit("figure", caption, src_id=fig.get("id"), label=label, graphics=graphics)

    def supplementary(self, sup: ET.Element) -> None:
        caption = sup.find(".//caption")
        if caption is not None:
            self.text_unit("supplementary", caption, src_id=sup.get("id"))

    def para(self, p: ET.Element) -> None:
        self.text_unit("para", p, src_id=p.get("id"))
        for fig in p.iter("fig"):
            self.figure(fig)
        for sup in p.iter("supplementary-material"):
            self.supplementary(sup)

    def container(self, el: ET.Element, level: int) -> None:
        self.heading(el.find("title"), level, el.get("id"))
        for ch in el:
            self.block(ch, level + 1)

    def block(self, el: ET.Element, level: int) -> None:
        if el.tag == "p":
            self.para(el)
        elif el.tag in CONTAINERS:
            self.container(el, level)
        elif el.tag == "fig":
            self.figure(el)
        elif el.tag == "supplementary-material":
            self.supplementary(el)

    def references(self, ref_list: ET.Element) -> None:
        self.heading(None, 2, ref_list.get("id"), fixed="References")
        for ref in ref_list.iter("ref"):
            self.add("ref", src_id=ref.get("id"), translate=False, source_md=_ref_md(ref))


def _ref_md(ref: ET.Element) -> str:
    label = (ref.findtext("label") or "").strip()
    cit = ref.find("element-citation")
    if cit is None:
        cit = ref.find("mixed-citation")
    if cit is None:
        return label
    parts = [label] if label else []
    if cit.tag == "element-citation":
        parts.append(_element_citation(cit))
    else:
        parts.append(_mixed_citation(cit))
    doi = next((e.text for e in cit.iter("pub-id") if e.get("pub-id-type") == "doi"), None)
    if doi:
        parts.append(f"doi:{doi}")
    return " ".join(p for p in parts if p)


def _element_citation(cit: ET.Element) -> str:
    names = [
        f"{n.findtext('surname', '')} {n.findtext('given-names', '')}".strip()
        for n in cit.iterfind(".//person-group[@person-group-type='author']/name")
    ]
    out = [", ".join(names) + "." if names else ""]
    out.extend(
        " ".join(cit.findtext(t).split()) + "."
        for t in ("article-title", "chapter-title")
        if cit.findtext(t)
    )
    if cit.findtext("source"):
        out.append(cit.findtext("source").strip() + ".")
    vol, fpage, lpage = (cit.findtext(t) for t in ("volume", "fpage", "lpage"))
    locator = (cit.findtext("year") or "") + (f";{vol}" if vol else "")
    if fpage:
        locator += f":{fpage}" + (f"–{lpage}" if lpage else "")
    out.append(locator + ".")
    return " ".join(p for p in out if p and p != ".")


def _mixed_citation(cit: ET.Element) -> str:
    text = cit.text or ""
    for ch in cit:
        if ch.tag != "pub-id":
            text += "".join(ch.itertext())
        text += ch.tail or ""
    return " ".join(text.split())


def digest(xml_text: str, protected: dict) -> list[dict]:
    root = fromstring(xml_text)
    article = root if root.tag == "article" else root.find("article")
    if article is None:
        raise ValueError("not a JATS article: no <article> element")
    d = _Digest(protected)
    meta = article.find("front/article-meta")
    if meta is not None:
        title = meta.find("title-group/article-title")
        if title is not None:
            d.text_unit("title", title, level=1)
        abstract = meta.find("abstract")
        if abstract is not None:
            d.heading(None, 2, abstract.get("id"), fixed="Abstract")
            for p in abstract.iter("p"):
                d.para(p)
    body = article.find("body")
    if body is not None:
        for ch in body:
            d.block(ch, 2)
    back = article.find("back")
    if back is not None:
        for ch in back:
            if ch.tag == "ref-list":
                d.references(ch)
            else:
                d.block(ch, 2)
    return d.units


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if len(args) != 1:
        print(__doc__, file=sys.stderr)
        return 2
    slug = args[0]
    units = digest(source_xml(slug).read_text(encoding="utf-8"), load_protected())
    out = work_dir(slug) / "units.json"
    out.write_text(json.dumps(units, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    translatable = sum(u["translate"] for u in units)
    print(f"{slug}: {len(units)} units ({translatable} translatable) -> {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
