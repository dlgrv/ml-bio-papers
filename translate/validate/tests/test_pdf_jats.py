"""Tests for translate/lib/pdf_jats.py heuristics."""

from translate.lib import pdf_jats as pj


def test_section_title_accepts_real_headings():
    assert pj._looks_like_section_title("1", "Introduction")
    assert pj._looks_like_section_title("3.1", "Unsupervised pre-training")
    assert pj._looks_like_section_title("2", "Related Work")


def test_section_title_rejects_table_noise():
    assert not pj._looks_like_section_title("83.3", "GenSen [64]")
    assert not pj._looks_like_section_title("4", "Table 1: Datasets")
    assert not pj._looks_like_section_title("2", "pre-trained language model as")
    assert not pj._looks_like_section_title("8", "[2] J. L. Ba")
