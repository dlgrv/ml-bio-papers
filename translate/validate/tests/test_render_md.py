from pathlib import Path

import pytest

from translate.steps.digest import jats_digest as jd
from translate.steps.render import render_md as rm

FIXTURE = Path(__file__).parent / "fixtures" / "mini_article.xml"
PROTECTED = {"terms": ["Kraken", "Kraken2"], "patterns": []}


def units():
    return jd.digest(FIXTURE.read_text(encoding="utf-8"), PROTECTED)


def identity(us):
    return {u["id"]: u["text"] for u in us if u["translate"]}


def test_original_render_matches_golden():
    us = units()
    got = rm.render(us, identity(us), original=True)
    golden = (Path(__file__).parent / "fixtures" / "mini_article.golden.md").read_text(
        encoding="utf-8"
    )
    assert got == golden


def test_headings_use_levels_and_title_is_h1():
    us = units()
    md = rm.render(us, identity(us), original=True)
    assert md.startswith("# Improved metagenomic analysis with Kraken 2\n")
    assert "\n## Methods\n" in md


def test_figure_caption_gets_label_and_figure_is_not_inside_paragraph():
    us = units()
    md = rm.render(us, identity(us), original=True)
    assert "**Fig. 1.** Differences in operation" in md
    para = next(line for line in md.split("\n\n") if line.startswith("Taxonomic classifiers"))
    assert "Differences in operation" not in para


def test_render_emits_image_markdown():
    us = units()
    md = rm.render(us, identity(us), original=True)
    assert "![Fig. 1](assets/13059_2019_1891_Fig1_HTML.jpg)" in md
    ru = rm.render(us, identity(us), original=False)
    assert "![Рис. 1](assets/13059_2019_1891_Fig1_HTML.jpg)" in ru


def test_russian_render_uses_fixed_headings_and_ru_figure_label():
    us = units()
    tr = {u["id"]: u["text"] for u in us if u["translate"]}
    md = rm.render(us, tr, original=False)
    assert "## Аннотация" in md
    assert "## Список литературы" in md
    assert "**Рис. 1.**" in md


def test_section_xref_resolves_to_translated_heading():
    us = units()
    tr = identity(us)
    methods = next(u for u in us if u["src_id"] == "Sec2")
    tr[methods["id"]] = "Методы"
    md = rm.render(us, tr, original=False)
    assert "раздел" not in md
    assert "“Методы”" in md


def test_section_xref_unmasks_placeholders_in_heading():
    us = units()
    tr = identity(us)
    methods = next(u for u in us if u["src_id"] == "Sec2")
    methods["spans"] = {"⟦N1⟧": {"type": "N", "md": "BERT"}}
    tr[methods["id"]] = "Методы ⟦N1⟧"
    md = rm.render(us, tr, original=False)
    assert "⟦N1⟧" not in md
    assert "Методы BERT" in md


def test_references_are_copied_verbatim_in_both_modes():
    us = units()
    refs = [u["source_md"] for u in us if u["kind"] == "ref"]
    for original in (True, False):
        md = rm.render(us, identity(us), original=original)
        assert "\n\n".join(refs) in md or "\n".join(refs) in md


def test_missing_translation_raises():
    us = units()
    tr = identity(us)
    tr.pop(us[0]["id"])
    with pytest.raises(KeyError, match=us[0]["id"]):
        rm.render(us, tr, original=False)
