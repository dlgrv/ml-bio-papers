import json

from translate.lib import glossary as gl
from translate.ops import glossary_build

README = """# Глоссарий

| Термин | Перевод | Примечание |
|---|---|---|
| k-mer | k-мер | |
| lowest common ancestor (LCA) | наименьший общий предок | note |
"""

README_GLOSS = """# Глоссарий

| Термин | Перевод | Примечание |
|---|---|---|
| read | рид | короткий фрагмент ДНК после секвенирования |
| MAG (metagenome-assembled genome) | MAG, метагеномный геном | не расшифровывать |
| species-level genome bin (SGB) | SGB | не переводить |
| reference database | референсная база | не «эталонная» |
"""


def _layout(tmp_path, readme=README, terms_json=None):
    gdir = tmp_path / "glossary"
    gdir.mkdir()
    (gdir / "README.md").write_text(readme, encoding="utf-8")
    if terms_json is not None:
        (gdir / "terms.json").write_text(
            json.dumps(terms_json, ensure_ascii=False, indent=1) + "\n", encoding="utf-8"
        )
    return str(tmp_path)


def test_build_writes_terms_json(tmp_path):
    root = _layout(tmp_path)
    path = glossary_build.build(root)
    assert path == tmp_path / "glossary" / "terms.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(data, list)
    assert len(data) == 2

    kmer = next(row for row in data if row["label"] == "k-mer")
    assert kmer["en"] == ["k-mer"]
    assert kmer["ru"] == ["k-мер"]
    assert kmer["ru_raw"] == "k-мер"
    assert kmer["note"] == ""
    assert kmer["ru_stems"] == [gl.stem("k-мер")]
    lca = next(row for row in data if "LCA" in row["label"])
    assert lca["en"] == ["lowest common ancestor", "LCA"]
    assert "наименьш" in lca["ru_stems"]


def test_load_prefers_terms_json(tmp_path):
    stub = [
        {
            "label": "from-json",
            "en": ["from-json"],
            "ru": ["из-json"],
            "ru_raw": "из-json",
            "note": "stub",
            "ru_stems": ["из-js"],
            "gloss": "reader definition",
            "paren_en": "never",
        }
    ]
    root = _layout(tmp_path, terms_json=stub)
    terms = gl.load(root)
    assert len(terms) == 1
    assert terms[0].label == "from-json"
    assert terms[0].ru == ("из-json",)
    assert terms[0].ru_stems == ("из-js",)
    assert terms[0].gloss == "reader definition"
    assert terms[0].paren_en == "never"


def test_load_terms_json_omitted_gloss_paren_en_use_defaults(tmp_path):
    stub = [
        {
            "label": "minimal",
            "en": ["minimal"],
            "ru": ["мин"],
            "ru_raw": "мин",
            "note": "",
            "ru_stems": ["ми"],
        }
    ]
    root = _layout(tmp_path, terms_json=stub)
    term = gl.load(root)[0]
    assert term.gloss == ""
    assert term.paren_en == "first"


def test_build_persists_gloss_and_paren_en(tmp_path):
    root = _layout(tmp_path, readme=README_GLOSS)
    data = json.loads(glossary_build.build(root).read_text(encoding="utf-8"))
    read = next(row for row in data if row["label"] == "read")
    assert read["gloss"] == "короткий фрагмент ДНК после секвенирования"
    assert read["note"] == ""
    mag = next(row for row in data if row["label"].startswith("MAG"))
    sgb = next(row for row in data if "SGB" in row["label"])
    assert mag["paren_en"] == "never"
    assert sgb["paren_en"] == "never"
    ref = next(row for row in data if row["label"] == "reference database")
    assert ref["gloss"] == ""
    assert "не" in ref["note"]


def test_load_fallback_readme(tmp_path, capsys):
    root = _layout(tmp_path)
    terms = gl.load(root)
    err = capsys.readouterr().err
    assert "WARN" in err
    assert "terms.json" in err

    assert [t.label for t in terms] == ["k-mer", "lowest common ancestor (LCA)"]
