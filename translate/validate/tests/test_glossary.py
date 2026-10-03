from pathlib import Path

import pytest

from translate.lib import glossary as gl

README = Path(__file__).resolve().parents[3] / "glossary" / "README.md"

TABLE = """# Глоссарий

| Термин | Перевод | Примечание |
|---|---|---|
| k-mer | k-мер | |
| lowest common ancestor (LCA) | наименьший общий предок | при первом употреблении — LCA |
| MAG (metagenome-assembled genome) | MAG, метагеномный геном | не расшифровывать |
| species-level genome bin (SGB) | SGB | не переводить |
| assembly | сборка (генома) | |
| reference database | референсная база | не «эталонная» |
| read | рид | короткий фрагмент ДНК после секвенирования |
"""


@pytest.fixture
def terms():
    return gl.parse(TABLE)


def by_en(terms, en):
    return next(t for t in terms if en in t.en)


def test_parse_reads_every_row(terms):
    assert len(terms) == 7


def test_parse_splits_abbreviation_and_alternatives(terms):
    lca = by_en(terms, "lowest common ancestor")
    assert set(lca.en) == {"lowest common ancestor", "LCA"}
    mag = by_en(terms, "MAG")
    assert mag.ru == ("MAG", "метагеномный геном")


def test_parse_drops_parenthetical_in_ru_for_matching(terms):
    assert by_en(terms, "assembly").ru == ("сборка",)


def test_terms_for_whole_word_and_plural(terms):
    got = {t.en[0] for t in gl.terms_for("We built k-mers from the assemblies.", terms)}
    assert got == {"k-mer"}  # 'assemblies' is not 'assembly' + s: no match is acceptable


def test_terms_for_ignores_markdown_emphasis_and_case(terms):
    got = gl.terms_for("The *k*-mer and the Lowest Common Ancestor", terms)
    assert {t.en[0] for t in got} == {"k-mer", "lowest common ancestor"}


def test_terms_for_not_inside_other_words(terms):
    assert gl.terms_for("Reassembly and the MAGnitude", terms) == []


def test_terms_for_abbreviation_matches(terms):
    assert [t.en[0] for t in gl.terms_for("assigned by LCA", terms)] == ["lowest common ancestor"]


def test_terms_for_longest_first_no_double_count(terms):
    text = "species-level genome bin"
    assert [t.en[0] for t in gl.terms_for(text, terms)] == ["species-level genome bin"]


def test_missing_in_translation_flags_absent_term(terms):
    src = "Each read gets a lowest common ancestor."
    assert [t.en[0] for t in gl.missing(src, "Каждому риду назначается предок.", terms)] == [
        "lowest common ancestor"
    ]


def test_missing_accepts_inflected_forms(terms):
    src = "the lowest common ancestor"
    assert gl.missing(src, "определяет наименьшего общего предка", terms) == []


def test_missing_accepts_any_alternative(terms):
    assert gl.missing("a MAG", "один метагеномный геном", terms) == []
    assert gl.missing("a MAG", "один MAG", terms) == []


def test_missing_k_mer_with_emphasis_normalised(terms):
    assert gl.missing("the *k*-mer", "*k*-мер", terms) == []
    assert gl.missing("the *k*-mers", "*k*-меры", terms) == []


def test_exceptions_suppress_a_term(terms):
    src = "the lowest common ancestor"
    assert gl.missing(src, "предок", terms, exceptions={"lowest common ancestor"}) == []


@pytest.mark.parametrize(
    ("word", "expected"),
    [
        ("предок", "пред"),
        ("сборка", "сбор"),
        ("общий", "общ"),
        ("риды", "рид"),
        ("ген", "ген"),
        ("MAG", "mag"),
    ],
)
def test_stem_rule(word, expected):
    assert gl.stem(word) == expected


def test_parse_splits_definition_gloss_vs_editorial_note(terms):
    read = by_en(terms, "read")
    assert read.gloss == "короткий фрагмент ДНК после секвенирования"
    assert read.note == ""
    ref = by_en(terms, "reference database")
    assert ref.gloss == ""
    assert "не" in ref.note
    lca = by_en(terms, "lowest common ancestor")
    assert lca.gloss == ""
    assert "при первом употреблении" in lca.note


def test_parse_paren_en_never_for_do_not_translate(terms):
    assert by_en(terms, "k-mer").paren_en == "first"
    assert by_en(terms, "read").paren_en == "first"
    assert by_en(terms, "MAG").paren_en == "never"
    assert by_en(terms, "species-level genome bin").paren_en == "never"


def test_term_dict_round_trips_gloss_and_paren_en(terms):
    read = by_en(terms, "read")
    mag = by_en(terms, "MAG")
    for term in (read, mag):
        back = gl.Term.from_dict(term.to_dict())
        assert back.gloss == term.gloss
        assert back.paren_en == term.paren_en
        assert back == term


def test_first_mention_form_with_and_without_gloss(terms):
    read = by_en(terms, "read")
    assert gl.first_mention_form(read) == "рид (read; короткий фрагмент ДНК после секвенирования)"
    kmer = by_en(terms, "k-mer")
    assert gl.first_mention_form(kmer) == "k-мер (k-mer)"
    assert gl.first_mention_form(by_en(terms, "MAG")) == "MAG, метагеномный геном"
    lca = by_en(terms, "lowest common ancestor")
    assert gl.first_mention_form(lca) == "наименьший общий предок"


def test_prompt_block_lists_only_matched_terms(terms):
    block = gl.prompt_block(gl.terms_for("a k-mer and LCA", terms))
    assert "k-mer → k-мер (k-mer)" in block
    assert "lowest common ancestor (LCA) → наименьший общий предок" in block
    assert "assembly" not in block


def test_prompt_block_first_use_includes_en_paren(terms):
    read = by_en(terms, "read")
    first = gl.prompt_block([read], introduced=frozenset())
    assert "read → рид (read; короткий фрагмент ДНК после секвенирования)" in first
    again = gl.prompt_block([read], introduced=frozenset({read.label}))
    assert "read → рид (read;" not in again
    assert "read → рид" in again


def test_prompt_block_empty_when_nothing_matched():
    assert gl.prompt_block([]) == ""


def test_real_readme_parses_and_has_no_duplicates():
    terms = gl.parse(README.read_text(encoding="utf-8"))
    assert len(terms) >= 25
    ens = [e.lower() for t in terms for e in t.en]
    assert len(ens) == len(set(ens)), "a term is defined twice in glossary/README.md"


def test_double_hyphen_after_unmask_still_matches():
    terms = gl.parse("| Термин | Перевод | Примечание |\n|---|---|---|\n| k-mer | k-мер | |\n")
    assert gl.missing("a k-mer", "один k--мер", terms) == []
