from pathlib import Path

import pytest

from translate.steps.digest import jats_digest as jd

FIXTURE = Path(__file__).parent / "fixtures" / "mini_article.xml"
FLOATS_FIXTURE = Path(__file__).parent / "fixtures" / "floats_group_article.xml"
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


def test_plos_mixed_citation_label_names_and_single_doi():
    xml = """
    <ref id="r1"><label>1</label><mixed-citation publication-type="journal">
    <name name-style="western"><surname>Knight</surname><given-names>R</given-names></name>,
    <name name-style="western"><surname>Vrbanac</surname><given-names>A</given-names></name>.
    <article-title>Best practices</article-title>. <source>Nat Rev Microbiol</source>.
    <year>2018</year>;<volume>16</volume>:<fpage>410</fpage>–<lpage>22</lpage>.
    <comment>doi: </comment><pub-id pub-id-type="doi">10.1038/s41579-018-0029-9</pub-id>
    <pub-id pub-id-type="pmid">29795328</pub-id>
    </mixed-citation></ref>
    """
    from defusedxml.ElementTree import fromstring

    md = jd._ref_md(fromstring(xml))
    assert md.startswith("1. Knight R, Vrbanac A.")
    assert "doi: doi:" not in md
    assert md.count("doi:10.1038/s41579-018-0029-9") == 1
    assert "29795328" not in md
    assert "KnightR" not in md


def test_citation_alternatives_prefers_mixed_citation_body():
    xml = """
    <ref id="CR9"><label>9.</label>
      <citation-alternatives>
        <element-citation publication-type="journal">
          <person-group person-group-type="author">
            <name name-style="western"><surname>Albertsen</surname><given-names>M</given-names></name>
            <etal/>
          </person-group>
          <article-title>Genome sequences of rare bacteria</article-title>
          <source>Nat. Biotechnol.</source>
          <year>2013</year>
          <volume>31</volume>
          <fpage>533</fpage>
          <lpage>538</lpage>
          <pub-id pub-id-type="doi">10.1038/nbt.2579</pub-id>
        </element-citation>
        <mixed-citation publication-type="journal">Albertsen, M. et al. Genome sequences of rare bacteria.
          <italic>Nat. Biotechnol.</italic><bold>31</bold>, 533–538 (2013).
          <pub-id pub-id-type="doi">10.1038/nbt.2579</pub-id>
        </mixed-citation>
      </citation-alternatives>
    </ref>
    """
    from defusedxml.ElementTree import fromstring

    md = jd._ref_md(fromstring(xml))
    assert md.startswith("9. Albertsen, M. et al.")
    assert "Nat. Biotechnol." in md
    assert "doi:10.1038/nbt.2579" in md
    assert md != "9."

    xml = """
    <ref id="r1"><label>1</label><mixed-citation publication-type="journal">
    <name name-style="western"><surname>Knight</surname><given-names>R</given-names></name>,
    <name name-style="western"><surname>Vrbanac</surname><given-names>A</given-names></name>.
    <article-title>Best practices</article-title>. <source>Nat Rev Microbiol</source>.
    <year>2018</year>;<volume>16</volume>:<fpage>410</fpage>–<lpage>22</lpage>.
    <comment>doi: </comment><pub-id pub-id-type="doi">10.1038/s41579-018-0029-9</pub-id>
    <pub-id pub-id-type="pmid">29795328</pub-id>
    </mixed-citation></ref>
    """
    from defusedxml.ElementTree import fromstring

    md = jd._ref_md(fromstring(xml))
    assert md.startswith("1. Knight R, Vrbanac A.")
    assert "doi: doi:" not in md
    assert md.count("doi:10.1038/s41579-018-0029-9") == 1
    assert "29795328" not in md
    assert "KnightR" not in md


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


def test_floats_group_figure_at_article_level():
    units = jd.digest(FLOATS_FIXTURE.read_text(encoding="utf-8"), PROTECTED)
    figs = [u for u in units if u["kind"] == "figure"]
    assert len(figs) == 1
    fig = figs[0]
    assert fig["label"].startswith(("Figure", "Fig"))
    assert fig["graphics"] == ["nihpp-demo-f0001.jpg"]
    assert "Feature encoding" in fig["text"]
    para_idx = next(i for i, u in enumerate(units) if u["kind"] == "para")
    fig_idx = next(i for i, u in enumerate(units) if u["kind"] == "figure")
    assert fig_idx > para_idx


def test_floats_group_dedupes_inline_and_floats():
    xml = """
    <article xmlns:xlink="http://www.w3.org/1999/xlink">
      <body>
        <sec>
          <p id="Par1">See the panel below.
            <fig id="F1" position="float">
              <label>Fig. 1</label>
              <caption><p>Shared caption.</p></caption>
              <graphic xlink:href="nihpp-demo-f0001.jpg"/>
            </fig>
          </p>
        </sec>
      </body>
      <floats-group>
        <fig id="F1" position="float">
          <label>Figure 1:</label>
          <caption><p>Shared caption.</p></caption>
          <graphic xlink:href="nihpp-demo-f0001.jpg"/>
        </fig>
      </floats-group>
    </article>
    """
    units = jd.digest(xml, PROTECTED)
    figs = [u for u in units if u["kind"] == "figure"]
    assert len(figs) == 1
