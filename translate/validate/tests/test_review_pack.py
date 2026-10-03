import json

from translate.ops import review_pack

SLUG = "2019-kraken2"


def _layout(tmp_path):
    root = tmp_path
    gdir = root / "glossary"
    gdir.mkdir()
    (gdir / "README.md").write_text(
        "| Термин | Перевод | Примечание |\n|---|---|---|\n| k-mer | k-мер | |\n",
        encoding="utf-8",
    )
    rules = root / "translate" / "rules"
    rules.mkdir(parents=True)
    (rules / "ru.json").write_text('{"banned_calques": []}\n', encoding="utf-8")
    wd = root / "translate" / "runs" / SLUG
    wd.mkdir(parents=True)
    units = [
        {
            "id": "u001",
            "kind": "para",
            "translate": True,
            "text": "We count each k-mer once.",
            "spans": {},
            "source_md": "We count each k-mer once.",
        },
        {
            "id": "u002",
            "kind": "ref",
            "translate": False,
            "text": "1. Doe J. Title.",
            "spans": {},
            "source_md": "1. Doe J. Title.",
        },
    ]
    (wd / "units.json").write_text(json.dumps(units), encoding="utf-8")
    (wd / "translated.json").write_text(
        json.dumps({"u001": {"status": "ok", "text": "Мы считаем каждый k-мер один раз."}}),
        encoding="utf-8",
    )
    return str(root)


def test_review_pack_sections(tmp_path):
    root = _layout(tmp_path)
    path = review_pack.write(SLUG, root)
    assert path == tmp_path / "translate" / "runs" / SLUG / "review.md"
    text = path.read_text(encoding="utf-8")

    assert f"# Review pack: {SLUG}" in text
    assert "## Units" in text
    assert "### u001 (para)" in text
    assert "**EN**" in text
    assert "We count each k-mer once." in text
    assert "**RU**" in text
    assert "Мы считаем каждый k-мер один раз." in text
    assert "**Glossary hits**" in text
    assert "k-mer → k-мер" in text
    assert "**Verify warnings**" in text
    assert "## MQM checklist" in text
    for section in ("Accuracy", "Terminology", "Fluency", "Hedging", "Numbers"):
        assert f"### {section}" in text
    assert "## Issues for repair" in text
    assert "### u002 (ref)" in text
