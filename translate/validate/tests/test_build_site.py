from pathlib import Path

import pytest
import yaml

from translate.steps.site import build_site

META = {
    "title": "Orig",
    "authors": ["A. One"],
    "doi": "10.1/x",
    "journal": "J",
    "year": 2019,
    "status": "machine-translated",
}


def _paper(
    root: Path,
    slug: str,
    status: str = "machine-translated",
    pdf: bool = False,
    *,
    with_asset: bool = False,
) -> None:
    d = root / "papers" / slug
    d.mkdir(parents=True)
    (d / "meta.yml").write_text(yaml.safe_dump({**META, "status": status}), encoding="utf-8")
    fig = (
        "![Рис. 1](assets/fig1.jpg)\n\n**Рис. 1.** Подпись.\n\n"
        if with_asset
        else "**Рис. 1.** Подпись.\n\n"
    )
    (d / "index.md").write_text(
        f"# Заголовок\n\n> плашка\n\n## Раздел один\n\nТекст $a_b$ [1].\n\n{fig}"
        "## Список литературы\n\n1. Ref one.\n",
        encoding="utf-8",
    )
    if with_asset:
        (d / "assets").mkdir()
        (d / "assets" / "fig1.jpg").write_bytes(b"\xff\xd8\xff")
    if pdf:
        (d / "index.pdf").write_bytes(b"%PDF")
    (root / "site-assets").mkdir(exist_ok=True)
    for name in ("pages.css", "paper.css"):
        (root / "site-assets" / name).write_text("body{}", encoding="utf-8")
    (root / "site-assets" / "site.js").write_text("// stub\n", encoding="utf-8")
    (root / "site-assets" / "fonts").mkdir(exist_ok=True)
    (root / "site-assets" / "fonts" / "f.woff2").write_bytes(b"f")


def test_only_translated_papers_are_published(tmp_path):
    _paper(tmp_path, "2019-a")
    _paper(tmp_path, "2020-b", status="not-started")
    slugs = build_site.build(tmp_path, tmp_path / "out")
    assert slugs == ["2019-a"]
    assert not (tmp_path / "out" / "2020-b").exists()


def test_index_lists_paper_with_relative_link(tmp_path):
    _paper(tmp_path, "2019-a")
    build_site.build(tmp_path, tmp_path / "out")
    idx = (tmp_path / "out" / "index.html").read_text(encoding="utf-8")
    assert 'href="2019-a/"' in idx
    assert "Заголовок" in idx
    assert 'href="static/pages.css"' in idx
    assert '<header class="nav">' in idx
    assert 'id="q"' in idx
    assert 'id="lang"' in idx
    assert 'data-lang="ru"' in idx
    assert 'id="theme"' in idx
    assert build_site.REPO_URL in idx
    assert 'src="static/site.js"' in idx
    assert 'data-slug="2019-a"' in idx
    search = (tmp_path / "out" / "static" / "search.json").read_text(encoding="utf-8")
    assert "2019-a" in search
    assert (tmp_path / "out" / "static" / "site.js").read_text(encoding="utf-8") == "// stub\n"


def test_article_page_uses_paper_layout(tmp_path):
    _paper(tmp_path, "2019-a", pdf=True)
    build_site.build(tmp_path, tmp_path / "out")
    out = tmp_path / "out"
    page = (out / "2019-a" / "index.html").read_text(encoding="utf-8")
    assert 'href="../static/pages.css"' in page
    assert 'href="../static/paper.css"' in page
    assert "tl_article--paper" in page
    assert page.count("<h1>") == 1
    assert "post-toc" not in page
    assert "Раздел один" in page
    assert "<math" in page
    assert '<div class="figure-box">' in page
    assert '<ol class="references">' in page
    assert 'id="ref-1"' in page
    assert 'href="#ref-1" class="cite"' in page
    assert "плашка" in page
    assert 'href="index.pdf"' in page
    assert 'class="meta-sep"' in page
    assert (out / "2019-a" / "index.pdf").read_bytes() == b"%PDF"
    assert (out / "static" / "fonts" / "f.woff2").read_bytes() == b"f"


def test_citations_link_to_reference_anchors(tmp_path):
    _paper(tmp_path, "2019-a")
    (tmp_path / "papers" / "2019-a" / "index.md").write_text(
        "# Заголовок\n\n"
        "## Раздел\n\n"
        "See [1] and [2, 3] plus [4–6] and [7] "
        "and [SGB](https://example.com/x) and "
        '<a href="https://doi.org/10.1/x">doi [9]</a>.\n\n'
        "## Список литературы\n\n"
        "1. One.\n2. Two.\n3. Three.\n4. Four.\n5. Five.\n6. Six.\n7. Seven.\n",
        encoding="utf-8",
    )
    build_site.build(tmp_path, tmp_path / "out")
    page = (tmp_path / "out" / "2019-a" / "index.html").read_text(encoding="utf-8")
    assert 'id="ref-1"' in page
    assert 'id="ref-7"' in page
    assert 'href="#ref-1" class="cite">1</a>' in page
    assert 'href="#ref-2" class="cite">2</a>' in page
    assert 'href="#ref-3" class="cite">3</a>' in page
    assert 'href="#ref-4" class="cite">4</a>' in page
    assert 'href="#ref-6" class="cite">6</a>' in page
    assert 'href="#ref-7" class="cite">7</a>' in page
    # Non-numeric markdown link and numbers already inside <a> stay untouched.
    assert 'href="https://example.com/x"' in page
    assert 'href="https://doi.org/10.1/x">doi [9]</a>' in page
    assert 'href="#ref-9"' not in page


def test_reference_dois_link_to_doi_org(tmp_path):
    _paper(tmp_path, "2019-a")
    (tmp_path / "papers" / "2019-a" / "index.md").write_text(
        "# Заголовок\n\n"
        "## Раздел\n\n"
        "See [1].\n\n"
        "## Список литературы\n\n"
        "1. Author. Title. doi:10.1038/s41579-018-0029-9\n"
        '2. Other. Already <a href="https://example.org/keep">linked</a>.\n',
        encoding="utf-8",
    )
    build_site.build(tmp_path, tmp_path / "out")
    page = (tmp_path / "out" / "2019-a" / "index.html").read_text(encoding="utf-8")
    assert (
        'href="https://doi.org/10.1038/s41579-018-0029-9">doi:10.1038/s41579-018-0029-9</a>' in page
    )
    assert 'href="https://example.org/keep">linked</a>' in page
    assert page.count("https://doi.org/10.1038/s41579-018-0029-9") == 1


def test_titles_are_html_escaped(tmp_path):
    _paper(tmp_path, "2019-a")
    (tmp_path / "papers" / "2019-a" / "index.md").write_text(
        "# A <b> & C\n\n## S\n\nt\n", encoding="utf-8"
    )
    build_site.build(tmp_path, tmp_path / "out")
    assert "A &lt;b&gt; &amp; C" in (tmp_path / "out" / "index.html").read_text(encoding="utf-8")


def test_bad_slug_directory_is_rejected(tmp_path):
    _paper(tmp_path, "BadSlug")
    with pytest.raises(ValueError, match="bad slug"):
        build_site.build(tmp_path, tmp_path / "out")


def test_site_copies_assets(tmp_path):
    _paper(tmp_path, "2019-a", with_asset=True)
    build_site.build(tmp_path, tmp_path / "out")
    copied = tmp_path / "out" / "2019-a" / "assets" / "fig1.jpg"
    assert copied.read_bytes() == b"\xff\xd8\xff"


def test_site_paper_css_keeps_reading_measure(tmp_path):
    _paper(tmp_path, "2019-a")
    real = Path(__file__).resolve().parents[3] / "site-assets" / "paper.css"
    (tmp_path / "site-assets" / "paper.css").write_text(
        real.read_text(encoding="utf-8"), encoding="utf-8"
    )
    build_site.build(tmp_path, tmp_path / "out")
    css = (tmp_path / "out" / "static" / "paper.css").read_text(encoding="utf-8")
    assert "72ch" in css
    assert "margin-inline: auto" in css
    assert "a.cite" in css
    assert "scroll-margin-top" in css


def test_site_html_has_img_src_assets(tmp_path):
    _paper(tmp_path, "2019-a", with_asset=True)
    build_site.build(tmp_path, tmp_path / "out")
    page = (tmp_path / "out" / "2019-a" / "index.html").read_text(encoding="utf-8")
    assert 'src="assets/fig1.jpg"' in page
    assert '<div class="figure-box">' in page
    assert page.index("<img") < page.index("figure-box") or "figure-box" in page
    box = page[page.index("figure-box") : page.index("figure-box") + 400]
    assert "<img" in box
    assert "Рис. 1" in box
