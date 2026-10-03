import pytest

from translate.lib import glossary as gl
from translate.steps.verify import verify_paper as vp

TERMS = gl.parse(
    "| Термин | Перевод | Примечание |\n|---|---|---|\n"
    "| lowest common ancestor (LCA) | наименьший общий предок | |\n"
    "| k-mer | k-мер | |\n"
    "| MAG (metagenome-assembled genome) | MAG, метагеномный геном | |\n"
)

TERMS_READ = gl.parse(
    "| Термин | Перевод | Примечание |\n|---|---|---|\n"
    "| read | рид | короткий фрагмент ДНК после секвенирования |\n"
    "| lowest common ancestor (LCA) | наименьший общий предок | |\n"
)


def u(uid, src, *, kind="para", translate=True, spans=None):
    return {
        "id": uid,
        "kind": kind,
        "translate": translate,
        "text": src,
        "spans": spans or {},
        "source_md": src,
    }


def check(src, ru, **kw):
    """Run the per-unit checks; return {check_name: severity}."""
    unit = u("u001", src, **kw)
    return {i.check: i.severity for i in vp.check_unit(unit, ru, TERMS)}


# ---- numbers -----------------------------------------------------------------------------
def test_identical_numbers_pass():
    assert (
        check(
            "The error was 0.95 at 85% and p < 0.05.", "Ошибка составила 0.95 при 85% и p < 0.05."
        )
        == {}
    )


@pytest.mark.parametrize(
    ("src", "ru", "label"),
    [
        ("score 0.95", "оценка 0.59", "changed"),
        ("n = 1000 reads", "n = 100 ридов", "changed"),
        ("p < 0.001", "p значимо", "lost"),
        ("a value", "значение 42", "added"),
        ("−5 °C", "-5 °C", "minus sign"),
        ("5–10 GB", "5-10 GB", "range dash"),
    ],
)
def test_number_mutations_fail(src, ru, label):
    assert check(src, ru).get("numbers") == "FAIL", label


def test_numbers_inside_placeholders_are_ignored():
    assert check("Fig ⟦F1⟧ 12", "Рис ⟦F1⟧ 12") == {}


def test_russian_notation_is_accepted():
    assert check("0.95", "0,95").get("numbers") == "FAIL"
    assert check("0.95 and 10", "0.95 и 10") == {}
    assert check("1,234 reads and 85%", "1\u202f234 рида и 85\u202f%") == {}
    assert check("10\u00a0GB", "10 ГБ") == {}


def test_number_word_order_may_change():
    assert check("12 reads and 34 genes", "34 гена и 12 ридов") == {}


# ---- negation and hedging ------------------------------------------------------------------
def test_negation_lost_fails():
    assert check("We did not find a difference.", "Мы нашли различие.").get("negation") == "FAIL"


def test_negation_added_warns():
    assert check("We found a difference.", "Мы не нашли различие.").get("negation") == "WARN"


@pytest.mark.parametrize(
    ("src", "ru"),
    [
        ("There is no bias.", "Смещения нет."),
        ("without error", "без ошибки"),
        ("It cannot be used.", "Это нельзя использовать."),
        ("We failed to detect it.", "Нам не удалось это обнаружить."),
    ],
)
def test_negation_kept_passes(src, ru):
    assert "negation" not in check(src, ru)


def test_hedging_strength_changed_warns():
    assert check("This may reduce memory.", "Это снижает объём памяти.").get("hedging") == "WARN"
    assert check("The data suggest a link.", "Данные доказывают связь.").get("hedging") == "WARN"


def test_hedging_kept_passes():
    assert "hedging" not in check("This may reduce memory.", "Это может снизить объём памяти.")


# ---- placeholders, links, formulas ----------------------------------------------------------
def test_leftover_placeholder_fails():
    assert check("see ⟦C1⟧", "см. ⟦C1⟧", spans={"⟦C1⟧": {"type": "C", "md": "[1]"}}) == {}
    # after unmask there must be none: checked on the final text
    assert vp.check_final_text("ok ⟦C1⟧")[0].check == "placeholder"


def test_untranslated_latin_paragraph_warns():
    long_en = "The quick brown fox jumps over the lazy dog many times."
    assert check(long_en, long_en).get("untranslated") == "WARN"


def test_short_latin_unit_is_not_flagged():
    assert "untranslated" not in check("Kraken 2", "Kraken 2")


def test_glossary_sees_term_hidden_behind_variable_placeholder():
    spans = {"⟦V1⟧": {"type": "V", "md": "*k*"}}
    unit = u("u001", "The ⟦V1⟧-mer length", spans=spans)
    bad = [i for i in vp.check_unit(unit, "Длина ⟦V1⟧-слова", TERMS) if i.check == "glossary"]
    assert bad
    assert not [i for i in vp.check_unit(unit, "Длина ⟦V1⟧-мера", TERMS) if i.check == "glossary"]


# ---- glossary --------------------------------------------------------------------------------
def test_glossary_term_missing_fails():
    assert check("the lowest common ancestor", "общий родитель").get("glossary") == "FAIL"


def test_glossary_term_present_inflected_passes():
    assert "glossary" not in check("the lowest common ancestor", "наименьшего общего предка")


# ---- banned calques ------------------------------------------------------------------------------
RULES = {"banned_calques": [{"bad": "имплементация", "good": "реализация"}]}


def test_banned_calque_without_gloss_fails():
    unit = u("u001", "implementation")
    issues = vp.check_unit(unit, "Имплементация метода.", TERMS, rules=RULES)
    assert [(i.check, i.severity) for i in issues] == [("banned_calque", "FAIL")]


def test_banned_calque_with_parenthetical_gloss_passes():
    unit = u("u001", "implementation")
    assert vp.check_unit(unit, "Имплементация (реализация) метода.", TERMS, rules=RULES) == []


# ---- paper level ---------------------------------------------------------------------------------
def test_structure_counts_must_match():
    src = [u("u001", "a", kind="heading"), u("u002", "b"), u("u003", "c", kind="figure")]
    ru = {"u001": "а", "u002": "б", "u003": "в"}
    assert vp.check_paper(src, ru, TERMS) == []
    del ru["u003"]
    assert any(
        i.check == "structure" and i.severity == "FAIL" for i in vp.check_paper(src, ru, TERMS)
    )


def test_citation_groups_in_rendered_body_identical_in_order():
    en = "reads [3, 7, 12] and [1–3] later [5]."
    assert vp.check_citations(en, "риды [3, 7, 12] и [1–3] позже [5].") == []
    assert vp.check_citations(en, "риды [7, 3, 12] и [1–3] позже [5].")[0].severity == "FAIL"
    assert vp.check_citations(en, "риды [3, 7, 12] и [1–3] позже.")[0].severity == "FAIL"


def test_abbreviation_expanded_once_per_paper():
    src = [u("u001", "lowest common ancestor (LCA)"), u("u002", "the LCA")]
    good = {"u001": "наименьший общий предок (LCA)", "u002": "LCA"}
    twice = {"u001": "наименьший общий предок (LCA)", "u002": "наименьший общий предок (LCA)"}
    assert vp.check_paper(src, good, TERMS) == []
    assert any(i.check == "abbrev" for i in vp.check_paper(src, twice, TERMS))


def _paper_issues(src_units, ru_dict, terms):
    return vp.check_paper(src_units, ru_dict, terms)


def test_first_mention_en_paren_on_first_use_passes():
    src = [u("u001", "Each read is assigned.")]
    ru = {"u001": "Каждому риду (read) назначается."}
    assert not [
        i
        for i in _paper_issues(src, ru, TERMS_READ)
        if i.check == "first_mention" and i.severity == "FAIL"
    ]


def test_first_mention_missing_en_paren_on_first_use_fails():
    src = [u("u001", "Each read is assigned.")]
    ru = {"u001": "Каждому риду назначается."}
    assert any(
        i.check == "first_mention" and i.severity == "FAIL"
        for i in _paper_issues(src, ru, TERMS_READ)
    )


def test_first_mention_repeated_en_paren_on_later_use_warns():
    src = [u("u001", "A read here."), u("u002", "Another read.")]
    ru = {"u001": "Рид (read) здесь.", "u002": "Ещё один рид (read)."}
    assert any(
        i.check in {"first_mention", "en_paren"} and i.severity == "WARN"
        for i in _paper_issues(src, ru, TERMS_READ)
    )


def test_first_mention_gloss_missing_after_en_paren_warns():
    src = [u("u001", "Each read is kept.")]
    ru = {"u001": "Каждый рид (read) сохраняется."}
    assert any(
        i.check == "gloss" and i.severity == "WARN" for i in _paper_issues(src, ru, TERMS_READ)
    )


def test_first_mention_lca_uses_abbrev_not_full_english():
    src = [u("u001", "lowest common ancestor (LCA)"), u("u002", "the LCA")]
    good = {"u001": "наименьший общий предок (LCA)", "u002": "LCA"}
    issues = _paper_issues(src, good, TERMS_READ)
    assert not [i for i in issues if i.check == "first_mention"]
    assert not [i for i in issues if i.check == "abbrev" and i.severity == "FAIL"]


def test_term_must_be_consistent_across_units():
    src = [u("u001", "a MAG"), u("u002", "a MAG")]
    inconsistent = {"u001": "один MAG", "u002": "один метагеномный геном"}
    assert any(i.check == "glossary" for i in vp.check_paper(src, inconsistent, TERMS))


def test_doi_and_urls_in_rendered_body_identical():
    en = "see https://doi.org/10.1/x and [a](https://g.com/a) doi:10.1093/bty648"
    ru = "см. https://doi.org/10.1/x и [а](https://g.com/a) doi:10.1093/bty648"
    assert vp.check_links(en, ru) == []
    bad = ru.replace("10.1093", "10.1099")
    assert vp.check_links(en, bad)[0].severity == "FAIL"


def test_link_order_interleaved_url_doi():
    en = "https://a.example/x doi:10.1093/aaa https://b.example/y"
    ru = "https://a.example/x https://b.example/y doi:10.1093/aaa"
    assert vp.check_links(en, ru)[0].severity == "FAIL"


def test_link_order_same_multiset_reordered():
    en = "https://a.example/x https://b.example/y"
    ru = "https://b.example/y https://a.example/x"
    assert vp.check_links(en, ru)[0].severity == "FAIL"


def test_missing_figure_image_markdown_fails():
    units = [{"id": "u1", "kind": "figure", "graphics": ["fig1.jpg"]}]
    en = "![Fig. 1](assets/fig1.jpg)\n\n**Fig. 1.** cap"
    ru = "**Рис. 1.** подпись"
    issues = vp.check_figures(units, en, ru)
    assert any(i.check == "figures" and i.severity == "FAIL" for i in issues)


def test_wrong_graphic_filename_fails():
    units = [{"id": "u1", "kind": "figure", "graphics": ["fig1.jpg"]}]
    en = "![Fig. 1](assets/other.jpg)\n\n**Fig. 1.** cap"
    ru = "![Рис. 1](assets/other.jpg)\n\n**Рис. 1.** подпись"
    issues = vp.check_figures(units, en, ru)
    assert any("fig1.jpg" in i.message for i in issues)


def test_references_byte_identical():
    en = "## References\n\n1. A. doi:10.1/x\n2. B."
    assert vp.check_refs(en, en) == []
    assert vp.check_refs(en, en.replace("B.", "Б."))[0].severity == "FAIL"


# ---- reporting -----------------------------------------------------------------------------------------
def test_exit_code_fail_over_warn():
    fail = vp.Issue("u1", "numbers", "FAIL", "x")
    warn = vp.Issue("u1", "hedging", "WARN", "x")
    assert vp.exit_code([fail, warn]) == 1
    assert vp.exit_code([warn]) == 2
    assert vp.exit_code([]) == 0


def test_hedge_alternatives_and_inflected_strong_words():
    assert "hedging" not in check("reads likely come from here", "риды, скорее всего, отсюда")
    assert "hedging" not in check("It is not possible to say.", "Нельзя сказать.")
    assert "hedging" not in check(
        "we define sensitivity", "мы определяем чувствительность на определённом уровне"
    )
    assert "hedging" not in check("demonstrating the advantage", "это подтверждает преимущество")
