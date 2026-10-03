from pathlib import Path

import pytest

from translate.steps.digest import jats_digest as jd

FIXTURE = Path(__file__).parent / "fixtures" / "mini_article.xml"
PROTECTED = {"terms": ["Kraken", "Kraken2"], "patterns": []}


@pytest.fixture(scope="module")
def units():
    return jd.digest(FIXTURE.read_text(encoding="utf-8"), PROTECTED)


def kinds(units):
    return [u["kind"] for u in units]


def test_order_title_abstract_body_back_refs(units):
    assert kinds(units) == [
        "title",
        "heading",  # Abstract
        "para",
        "heading",  # Background
        "para",
        "figure",
        "heading",  # Methods
        "para",
        "para",
        "para",
        "supplementary",
        "heading",  # Acknowledgements
        "para",
        "heading",  # References
        "ref",
        "ref",
    ]


def test_ids_are_sequential_and_unique(units):
    ids = [u["id"] for u in units]
    assert ids == [f"u{n:03d}" for n in range(1, len(units) + 1)]


def test_title_is_h1_and_headings_levels(units):
    assert units[0]["level"] == 1
    assert [u["level"] for u in units if u["kind"] == "heading"] == [2, 2, 2, 2, 2]


def test_heading_keeps_sec_id_for_xref_resolution(units):
    assert {u["src_id"] for u in units if u["kind"] == "heading"} >= {"Sec1", "Sec2"}


def test_figure_is_extracted_from_paragraph_with_label(units):
    para = next(u for u in units if u["src_id"] == "Par2")
    assert "Differences in operation" not in para["source_md"]
    fig = next(u for u in units if u["kind"] == "figure")
    assert fig["label"] == "Fig. 1"
    assert fig["text"].startswith("Differences in operation between the two versions of ")


def test_figure_graphics_from_href(units):
    fig = next(u for u in units if u["kind"] == "figure")
    assert fig["graphics"] == ["13059_2019_1891_Fig1_HTML.jpg"]


def test_supplementary_caption_is_a_unit(units):
    sup = next(u for u in units if u["kind"] == "supplementary")
    assert "Comparison of accuracy and computational performance" in sup["text"]
    assert sup["translate"] is True


def test_refs_are_not_translated_and_have_stable_markdown(units):
    refs = [u for u in units if u["kind"] == "ref"]
    assert [r["translate"] for r in refs] == [False, False]
    assert refs[0]["source_md"] == (
        "1. Kim D, Song L. Centrifuge: rapid and sensitive classification of metagenomic "
        "sequences. Genome Res. 2016;26:1721–1729. doi:10.1101/gr.210641.116"
    )
    assert refs[1]["source_md"].startswith("2. Langmead B, Wilks C. Scaling read aligners")
    assert refs[1]["source_md"].endswith("doi:10.1093/bioinformatics/bty648")


def test_translatable_units_have_masked_text_and_spans(units):
    para = next(u for u in units if u["src_id"] == "Par2")
    assert "⟦C1⟧" in para["text"]
    assert para["spans"]["⟦C1⟧"]["md"] == "[1–3]"


def test_untranslatable_units_have_no_text(units):
    assert all(u["text"] == "" for u in units if not u["translate"])


def test_formula_paragraph_is_split_around_formula_without_loss(units):
    par = next(u for u in units if u["src_id"] == "Par4")
    assert "⟦M1⟧" in par["text"]
    assert (
        par["spans"]["⟦M1⟧"]["md"].strip()
        == "$$\\mathrm{MAPE}=\\frac{100\\%}{n}\\sum \\limits_{x=1}^n\\left|\\frac{T_x-{S}_x}{T_x}\\right|$$"
    )


def test_non_article_is_rejected():
    with pytest.raises(ValueError, match="article"):
        jd.digest("<html/>", PROTECTED)


def test_every_paragraph_is_covered_exactly_once(units):
    src = [u["src_id"] for u in units if u["kind"] == "para"]
    assert len(src) == len(set(src))
    assert {"Par1", "Par2", "Par3", "Par4", "Par5"} <= set(src)
