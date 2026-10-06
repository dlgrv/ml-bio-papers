from pathlib import Path

import pytest
from defusedxml.ElementTree import fromstring

from translate.lib import latexml_jats as lx
from translate.steps.digest import jats_digest as jd

FIXTURE = Path(__file__).parent / "fixtures" / "mini_latexml.html"
PROTECTED = {"terms": ["Mini", "BERT"], "patterns": []}


def _article():
    xml = lx.html_to_jats(FIXTURE.read_text(encoding="utf-8"))
    return fromstring(xml)


def test_html_to_jats_is_article_with_front_body_back():
    root = _article()
    assert root.tag == "article"
    assert root.findtext("front/article-meta/title-group/article-title") == (
        "Mini Transformer Paper"
    )
    assert root.find("front/article-meta/abstract/p") is not None
    assert root.find("body/sec/title") is not None
    assert root.find("back/ref-list/ref") is not None


def test_citations_become_bibr_xrefs():
    p = _article().find("front/article-meta/abstract/p")
    xrefs = list(p.iter("xref"))
    assert [el.get("ref-type") for el in xrefs] == ["bibr"]
    assert xrefs[0].get("rid") == "bib.bib1"
    assert "Devlin" in "".join(xrefs[0].itertext())


def test_links_bold_italic_monospace_and_figure_graphic():
    jats = lx.html_to_jats(FIXTURE.read_text(encoding="utf-8"))
    root = fromstring(jats)
    intro = root.find("body/sec/p")
    assert intro.find("ext-link") is not None
    assert intro.find("italic") is not None
    assert intro.find("monospace") is not None
    fig = root.find("body/sec/fig")
    assert fig.find("caption") is not None
    graphic = fig.find("graphic")
    assert graphic is not None
    href = graphic.get("{http://www.w3.org/1999/xlink}href")
    assert href.endswith("fig1.svg")


def test_digest_order_skips_chrome():
    xml = lx.html_to_jats(FIXTURE.read_text(encoding="utf-8"))
    kinds = [u["kind"] for u in jd.digest(xml, PROTECTED)]
    assert kinds == [
        "title",
        "heading",  # Abstract
        "para",
        "heading",  # Introduction
        "para",
        "figure",
        "heading",  # Details
        "para",
        "heading",  # References
        "ref",
    ]
    assert "chrome" not in xml


def test_rejects_html_without_ltx_article():
    with pytest.raises(ValueError, match="ltx_document"):
        lx.html_to_jats("<html><body><p>nope</p></body></html>")
