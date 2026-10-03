from translate.steps.publish import build_paper

META = {
    "authors": ["A. One", "B. Two"],
    "title": "T",
    "journal": "J",
    "year": 2019,
    "doi": "10.1/x",
    "license": "CC BY 4.0",
}


def test_header_is_minimal_attribution():
    h = build_paper.header(META)
    assert h.startswith("> **Неофициальный перевод.**")
    assert "https://doi.org/10.1/x" in h
    assert "CC BY 4.0" in h
    assert "Оригинал главнее" not in h
    assert "assets/" not in h
    assert "Hy-MT2" not in h
    assert "ожидает вычитки" not in h
    assert "Рисунки:" not in h
    assert h.endswith("\n\n")


def test_header_omits_pmc_assets_line_even_when_pmcid_present():
    h = build_paper.header({**META, "pmcid": "PMC6883579"})
    assert "PMC6883579" not in h
    assert "assets/" not in h
