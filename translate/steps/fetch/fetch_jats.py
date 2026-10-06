#!/usr/bin/env python3
"""Download paper XML into translate/runs/<slug>/source.xml.

Source is `pmcid` (PMC JATS via E-utilities) or `arxiv` (LaTeXML HTML → JATS)
from papers/<slug>/meta.yml.
Usage: fetch_jats.py <slug>
"""

from __future__ import annotations

import os
import re
import sys
from typing import TYPE_CHECKING

import yaml
from defusedxml.ElementTree import ParseError, fromstring

from translate.lib.http import download
from translate.lib.latexml_jats import html_to_jats
from translate.lib.paths import meta_yml, source_xml

if TYPE_CHECKING:
    from pathlib import Path

EFETCH = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
PMCID_RE = re.compile(r"PMC(\d+)")
ARXIV_RE = re.compile(r"^(\d{4}\.\d{4,5})(v\d+)?$")


def efetch_url(pmcid: str) -> str:
    m = PMCID_RE.fullmatch(pmcid)
    if not m:
        raise ValueError(f"bad PMCID {pmcid!r}: expected PMC<digits>")
    return f"{EFETCH}?db=pmc&id={m.group(1)}&retmode=xml"


def validate(data: bytes) -> None:
    """Accept only a document that contains a JATS <article>."""
    try:
        root = fromstring(data)
    except ParseError as e:
        raise ValueError(f"response is not an article: {e}") from e
    if root.tag != "article" and root.find("article") is None:
        raise ValueError("response is not an article: no <article> element")


def arxiv_html_url(arxiv: str) -> str:
    m = ARXIV_RE.fullmatch(str(arxiv).strip())
    if not m:
        raise ValueError(f"bad arxiv id {arxiv!r}: expected YYYY.NNNNN with optional vN")
    return f"https://export.arxiv.org/html/{m.group(1)}{m.group(2) or ''}"


def _from_arxiv_html(raw: bytes) -> bytes:
    try:
        html = raw.decode("utf-8")
    except UnicodeDecodeError as e:
        raise ValueError("arxiv response is not UTF-8 HTML") from e
    return html_to_jats(html).encode("utf-8")


def fetch(slug: str, root: str | None = None) -> Path:
    meta = yaml.safe_load(meta_yml(slug, root).read_text(encoding="utf-8")) or {}
    pmcid = meta.get("pmcid")
    arxiv = meta.get("arxiv")
    if pmcid:
        data = download(efetch_url(str(pmcid)))
    elif arxiv:
        data = _from_arxiv_html(download(arxiv_html_url(str(arxiv))))
    else:
        raise ValueError(f"{meta_yml(slug, root)}: no pmcid or arxiv")
    validate(data)
    out = source_xml(slug, root)
    out.parent.mkdir(parents=True, exist_ok=True)
    tmp = out.with_suffix(".xml.tmp")
    tmp.write_bytes(data)
    os.replace(tmp, out)
    return out


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if len(args) != 1:
        print(__doc__, file=sys.stderr)
        return 2
    out = fetch(args[0])
    print(f"{args[0]}: {out.stat().st_size} bytes -> {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
