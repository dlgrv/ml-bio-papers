import pytest
from defusedxml.ElementTree import fromstring

from translate.lib import mask

PROTECTED = {"terms": ["Kraken", "Bracken"], "patterns": [r"PRJNA\d+"]}
NS = 'xmlns:xlink="http://www.w3.org/1999/xlink" xmlns:mml="http://www.w3.org/1998/Math/MathML"'


def p(inner):
    return fromstring(f"<p {NS}>{inner}</p>")


def run(inner):
    text, spans = mask.mask(p(inner), PROTECTED)
    return text, spans


def test_plain_text_passes_through():
    text, spans = run("A plain sentence.")
    assert text == "A plain sentence."
    assert spans == {}


def test_single_letter_italic_is_atomic_variable():
    text, spans = run('The <italic toggle="yes">k</italic>-mer length.')
    assert text == "The ⟦V1⟧-mer length."
    assert mask.unmask(text, spans) == "The *k*-mer length."


def test_longer_italic_becomes_markdown_not_placeholder():
    text, spans = run("A <italic>novel approach</italic> here.")
    assert text == "A *novel approach* here."
    assert spans == {}


def test_species_name_in_italic_is_protected():
    text, spans = run("<italic>Escherichia coli</italic> was used.")
    assert text == "⟦N1⟧ was used."
    assert mask.unmask(text, spans) == "*Escherichia coli* was used."


def test_bold_becomes_markdown():
    text, _ = run("<bold>a</bold> Both versions")
    assert text == "**a** Both versions"


def test_citation_group_is_one_span_with_brackets():
    inner = (
        'reads [<xref ref-type="bibr" rid="CR1">1</xref>–<xref ref-type="bibr" rid="CR3">3</xref>].'
    )
    text, spans = run(inner)
    assert text == "reads ⟦C1⟧."
    assert mask.unmask(text, spans) == "reads [1–3]."


def test_citation_list_with_commas():
    inner = '[<xref ref-type="bibr" rid="CR6">6</xref>, <xref ref-type="bibr" rid="CR7">7</xref>]'
    text, spans = run(inner)
    assert mask.unmask(text, spans) == "[6, 7]"
    assert len(spans) == 1


def test_figure_media_xrefs_keep_their_number():
    inner = '(Fig. <xref rid="Fig1" ref-type="fig">1</xref>a, Additional file <xref rid="M1" ref-type="media">1</xref>)'
    text, spans = run(inner)
    assert text == "(Fig. ⟦F1⟧a, Additional file ⟦F2⟧)"
    assert mask.unmask(text, spans) == "(Fig. 1a, Additional file 1)"


def test_section_xref_resolves_to_translated_title():
    text, spans = run('the “<xref rid="Sec2" ref-type="sec">Methods</xref>” section')
    assert mask.unmask(text, spans, titles={"Sec2": "Методы"}) == "the “Методы” section"
    assert spans["⟦R1⟧"]["rid"] == "Sec2"


def test_ext_link_renders_markdown_and_cleans_pmc_artifact():
    inner = '<ext-link ext-link-type="uri" xlink:href="https://github.com/x/y%3e">https://github.com/x/y&gt;</ext-link>.'
    text, spans = run(inner)
    assert text == "⟦L1⟧."
    assert mask.unmask(text, spans) == "[https://github.com/x/y](https://github.com/x/y)."


def test_sub_and_sup_are_atomic():
    text, spans = run('n<sub><italic toggle="yes">x</italic></sub> = 1.5 × 10<sup>−3</sup>')
    assert text == "n⟦U1⟧ = 1.5 × 10⟦U2⟧"
    assert mask.unmask(text, spans) == "n<sub>*x*</sub> = 1.5 × 10<sup>−3</sup>"


def test_display_formula_uses_tex():
    inner = (
        'error:<disp-formula id="E"><alternatives><tex-math>\\begin{document}$$ a=b $$\\end{document}'
        "</tex-math><mml:math><mml:mi>a</mml:mi></mml:math></alternatives></disp-formula>where"
    )
    text, spans = run(inner)
    assert text == "error:⟦M1⟧where"
    assert mask.unmask(text, spans) == "error:\n\n$$a=b$$\n\nwhere"


def test_protected_term_and_pattern_masked_in_plain_text():
    text, spans = run("Kraken 2 and Bracken used PRJNA12345.")
    assert text == "⟦N1⟧ 2 and ⟦N2⟧ used ⟦N3⟧."
    assert mask.unmask(text, spans) == "Kraken 2 and Bracken used PRJNA12345."


def test_protected_term_is_whole_word_only():
    text, _ = run("Krakens and Brackenridge")
    assert "⟦" not in text


def test_nested_italic_around_protected_term():
    text, spans = run("<italic>Kraken</italic>")
    assert mask.unmask(text, spans) == "*Kraken*"


def test_thin_and_nbsp_whitespace_preserved():
    text, _ = run("100\u2009GB and Fig.\u00a01")
    assert text == "100\u2009GB and Fig.\u00a01"


@pytest.mark.parametrize(
    "inner",
    [
        'a <italic toggle="yes">k</italic>-mer [<xref ref-type="bibr" rid="C1">1</xref>] and <bold>b</bold>',
        '<italic>Escherichia coli</italic> (Fig. <xref rid="F" ref-type="fig">2</xref>)',
        "x<sub>1</sub> y<sup>2</sup> Kraken",
    ],
)
def test_round_trip_equals_direct_markdown(inner):
    text, spans = run(inner)
    assert mask.unmask(text, spans) == mask.to_markdown(p(inner), PROTECTED)


def test_check_placeholders_ok_when_multiset_equal_any_order():
    mask.check_placeholders("b ⟦V2⟧ a ⟦V1⟧", "x ⟦V1⟧ y ⟦V2⟧")


def test_missing_placeholder_detected():
    with pytest.raises(mask.PlaceholderError, match="missing"):
        mask.check_placeholders("a ⟦V1⟧", "a ⟦V1⟧ ⟦V2⟧")


def test_duplicated_placeholder_detected():
    with pytest.raises(mask.PlaceholderError, match="duplicated"):
        mask.check_placeholders("⟦V1⟧ ⟦V1⟧", "⟦V1⟧")


def test_invented_placeholder_detected():
    with pytest.raises(mask.PlaceholderError, match="unknown"):
        mask.check_placeholders("⟦V9⟧", "a")
