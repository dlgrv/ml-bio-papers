#!/usr/bin/env python3
"""Build the static site: site/index.html (paper list) and site/<slug>/index.html (one paper each).

Usage: build_site.py [out_dir]   (default: site/ in the repo root). Needs pandoc on PATH.
Only papers whose meta.yml status is not "not-started" are published.
The look is the dlgrv.com notes look: site-assets/pages.css is a copy of its pages.css.
"""

from __future__ import annotations

import html
import json
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

import yaml

from translate.lib.config import default_root
from translate.lib.paths import check_slug

if TYPE_CHECKING:
    from collections.abc import Callable

SITE_TITLE = "ml-papers"
REPO_URL = "https://github.com/dlgrv/ml-papers"
UNPUBLISHED = "not-started"
# Byline/meta field separator: middot is the publishing-industry default.
META_SEP = " · "
TAG_RE = re.compile(r"<[^>]+>")

_GH_SVG = (
    '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" '
    'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'
    '<path d="M15 22v-4a4.8 4.8 0 0 0-1-3.5c3 0 6-2 6-5.5.08-1.25-.27-2.48-1-3.5'
    ".28-1.15.28-2.35 0-3.5 0 0-1 0-3 1.5-2.64-.5-5.36-.5-8 0C6 2 5 2 5 2c-.3 1.15"
    "-.3 2.35 0 3.5A5.403 5.403 0 0 0 4 9c0 3.5 3 5.5 6 5.5-.39.49-.68 1.05-.85 "
    '1.65-.17.6-.22 1.23-.15 1.85v4"/><path d="M9 18c-4.51 2-5-2-7-2"/></svg>'
)
_SUN_SVG = (
    '<svg class="sun" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
    'stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'
    '<circle cx="12" cy="12" r="4"/><path d="M12 2v2"/><path d="M12 20v2"/>'
    '<path d="m4.93 4.93 1.41 1.41"/><path d="m17.66 17.66 1.41 1.41"/>'
    '<path d="M2 12h2"/><path d="M20 12h2"/>'
    '<path d="m19.07 4.93-1.41 1.41"/><path d="m6.34 17.66-1.41 1.41"/></svg>'
)
_MOON_SVG = (
    '<svg class="moon" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
    'stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'
    '<path d="M12 3a6 6 0 0 0 9 9 9 9 0 1 1-9-9Z"/></svg>'
)
_SEARCH_SVG = (
    '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" '
    'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'
    '<circle cx="11" cy="11" r="8"/><path d="m21 21-4.3-4.3"/></svg>'
)
_CHEVRON_SVG = (
    '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" '
    'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'
    '<path d="m6 9 6 6 6-6"/></svg>'
)


@dataclass(frozen=True)
class Paper:
    slug: str
    title_ru: str
    meta: dict
    body_md: str
    has_pdf: bool

    @property
    def authors(self) -> str:
        return ", ".join(self.meta.get("authors") or [])

    @property
    def topics(self) -> list[str]:
        raw = self.meta.get("topics") or []
        return [t for t in raw if isinstance(t, str) and t]


def topics_suffix(topics: list[str]) -> str:
    """Inline topic chips for meta lines (empty if no topics)."""
    if not topics:
        return ""
    chips = META_SEP.join(f'<span class="topic-chip">{html.escape(t)}</span>' for t in topics)
    return f"{META_SEP}{chips}"


def load_papers(root: Path) -> list[Paper]:
    papers = []
    for d in sorted((root / "papers").iterdir()):
        meta_path = d / "meta.yml"
        if not (d.is_dir() and meta_path.exists()):
            continue
        meta = yaml.safe_load(meta_path.read_text(encoding="utf-8")) or {}
        if meta.get("status", UNPUBLISHED) == UNPUBLISHED:
            continue
        index = d / "index.md"
        if not index.exists():
            continue
        md = index.read_text(encoding="utf-8")
        title, _, body = md.partition("\n")
        papers.append(
            Paper(
                check_slug(d.name),
                title.lstrip("# ").strip(),
                meta,
                body.lstrip("\n"),
                (d / "index.pdf").exists(),
            )
        )
    return sorted(papers, key=lambda p: (-int(p.meta.get("year") or 0), p.slug))


def pandoc_html(md: str) -> str:
    out = subprocess.run(
        [
            "pandoc",
            "-f",
            "markdown+tex_math_dollars+pipe_tables",
            "-t",
            "html5",
            "--mathml",
            "--section-divs",
            "--wrap=none",
        ],
        input=md,
        capture_output=True,
        text=True,
        check=True,
    )
    return out.stdout


H2_RE = re.compile(r'<section id="([^"]+)" class="level2">\s*<h2>(.*?)</h2>', re.DOTALL)
# Pandoc wraps MD images as <figure><img/><figcaption/></figure>; our caption is the next <p>.
FIG_WITH_IMG_RE = re.compile(
    r"<figure>\s*(<img\b[^>]*>)\s*(?:<figcaption[^>]*>.*?</figcaption>\s*)?</figure>\s*"
    r"<p>(<strong>(?:Рис|Fig|Таблица)\.? [^<]*</strong>.*?)</p>",
    re.DOTALL,
)
FIG_CAPTION_ONLY_RE = re.compile(
    r"<p>(<strong>(?:Рис|Fig|Таблица)\.? [^<]*</strong>.*?)</p>",
    re.DOTALL,
)
OL_RE = re.compile(r"(<h2>Список литературы</h2>\s*)<ol[^>]*>")
REFS_OL_RE = re.compile(r'(<ol class="references">)(.*?)(</ol>)', re.DOTALL)
LI_OPEN_RE = re.compile(r"<li\b([^>]*)>", re.IGNORECASE)
CITE_GROUP_RE = re.compile(r"\[(\d+(?:\s*[,–-]\s*\d+)*)\]")
CITE_NUM_RE = re.compile(r"\d+")
A_TAG_RE = re.compile(r"<a\b[^>]*>.*?</a>", re.DOTALL | re.IGNORECASE)
DOI_TOKEN_RE = re.compile(r"doi:(10\.\d+/[^\s<]+)", re.IGNORECASE)
IMG_TAG_RE = re.compile(r"<img\b([^>]*)>", re.IGNORECASE)


def split_note(md: str) -> tuple[str, str]:
    """Split the leading `> ...` translation note from the paper body."""
    lines = md.split("\n")
    n = 0
    while n < len(lines) and lines[n].startswith(">"):
        n += 1
    return "\n".join(x.lstrip("> ").rstrip() for x in lines[:n]), "\n".join(lines[n:]).lstrip("\n")


def map_outside_a_tags(html: str, transform: Callable[[str], str]) -> str:
    parts: list[str] = []
    last = 0
    for m in A_TAG_RE.finditer(html):
        parts.append(transform(html[last : m.start()]))
        parts.append(m.group(0))
        last = m.end()
    parts.append(transform(html[last:]))
    return "".join(parts)


def anchor_references(body: str) -> str:
    """Add id=\"ref-N\" to each <li> under ol.references (1-based list order)."""

    def on_ol(m: re.Match[str]) -> str:
        n = 0

        def on_li(lm: re.Match[str]) -> str:
            nonlocal n
            n += 1
            attrs = lm.group(1)
            if re.search(r"\bid\s*=", attrs, re.IGNORECASE):
                return lm.group(0)
            return f'<li id="ref-{n}"{attrs}>'

        return m.group(1) + LI_OPEN_RE.sub(on_li, m.group(2)) + m.group(3)

    return REFS_OL_RE.sub(on_ol, body)


def _link_cite_nums(inner: str) -> str:
    return CITE_NUM_RE.sub(
        lambda m: f'<a href="#ref-{m.group(0)}" class="cite">{m.group(0)}</a>',
        inner,
    )


def _linkify_cites(text: str) -> str:
    return CITE_GROUP_RE.sub(lambda m: "[" + _link_cite_nums(m.group(1)) + "]", text)


def link_citations(body: str) -> str:
    """Wrap in-text [n]/[n,m]/[n–m] as links to #ref-N."""
    return map_outside_a_tags(body, _linkify_cites)


def _link_doi_token(text: str) -> str:
    return DOI_TOKEN_RE.sub(
        lambda m: f'<a href="https://doi.org/{m.group(1)}">doi:{m.group(1)}</a>',
        text,
    )


def link_reference_dois(body: str) -> str:
    def on_ol(m: re.Match[str]) -> str:
        return m.group(1) + map_outside_a_tags(m.group(2), _link_doi_token) + m.group(3)

    return REFS_OL_RE.sub(on_ol, body)


def _lazy_img(m: re.Match[str]) -> str:
    attrs = m.group(1)
    if re.search(r"\bloading\s*=", attrs, re.IGNORECASE):
        return m.group(0)
    return f'<img loading="lazy" decoding="async"{attrs}>'


def decorate(body: str) -> str:
    body = FIG_WITH_IMG_RE.sub(
        r'<div class="figure-box"><p>\1</p><p>\2</p></div>',
        body,
    )

    def wrap_caption(m: re.Match[str]) -> str:
        # Skip captions already inside a .figure-box (from FIG_WITH_IMG_RE).
        opened = body.rfind('<div class="figure-box">', 0, m.start())
        closed = body.rfind("</div>", 0, m.start())
        if opened > closed:
            return m.group(0)
        return f'<div class="figure-box"><p>{m.group(1)}</p></div>'

    body = FIG_CAPTION_ONLY_RE.sub(wrap_caption, body)
    body = IMG_TAG_RE.sub(_lazy_img, body)
    body = OL_RE.sub(r'\1<ol class="references">', body)
    body = anchor_references(body)
    body = link_reference_dois(body)
    return link_citations(body)


def shell(title: str, description: str, article: str, *, depth: int) -> str:
    up = "../" * depth
    home = "./" if depth == 0 else "../"
    extra_css = f'    <link rel="stylesheet" href="{up}static/paper.css" />\n' if depth else ""
    return f"""<!doctype html>
<html lang="ru">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <script>(function(){{try{{var s=localStorage.getItem('theme');var d=s?s==='dark':matchMedia('(prefers-color-scheme: dark)').matches;if(d)document.documentElement.classList.add('dark')}}catch(e){{}}}})();</script>
    <title>{html.escape(title)}</title>
    <meta name="description" content="{html.escape(description, quote=True)}" />
    <meta name="theme-color" content="#ffffff" media="(prefers-color-scheme: light)" />
    <meta name="theme-color" content="#111111" media="(prefers-color-scheme: dark)" />
    <link rel="stylesheet" href="{up}static/pages.css" />
{extra_css}  </head>
  <body>
    <header class="nav">
      <div class="nav-in">
        <a class="nav-title" href="{home}">Papers</a>
        <label class="search">
          {_SEARCH_SVG}
          <input id="q" type="search" placeholder="Поиск по статьям" autocomplete="off" aria-label="Поиск по статьям" />
          <kbd>/</kbd>
          <div id="search-results" class="search-results" hidden></div>
        </label>
        <div class="nav-r">
          <details class="lang-dd" id="lang">
            <summary title="Язык" aria-label="Выбрать язык"><span id="lang-label">РУ</span>{_CHEVRON_SVG}</summary>
            <div class="lang-menu" role="menu">
              <button type="button" role="menuitem" data-lang="ru" aria-current="true">Русский</button>
            </div>
          </details>
          <a class="icon-btn" href="{REPO_URL}" target="_blank" rel="noopener" title="Репозиторий на GitHub" aria-label="GitHub">{_GH_SVG}</a>
          <button type="button" class="icon-btn theme-btn" id="theme" aria-label="Переключить тёмную тему" title="Переключить тёмную тему">{_SUN_SVG}{_MOON_SVG}</button>
        </div>
      </div>
    </header>
    <main class="tl_page">
{article}
    </main>
    <script src="{up}static/site.js" defer></script>
  </body>
</html>
"""


def render_index(papers: list[Paper]) -> str:
    items = "".join(
        f"""
          <li data-slug="{html.escape(p.slug)}">
            <a class="paper-link" href="{p.slug}/">{html.escape(p.title_ru)}</a>
            <div class="blog-index__meta">{html.escape(p.authors)}{META_SEP}{html.escape(str(p.meta.get("journal", "")))}, {p.meta.get("year", "")}{topics_suffix(p.topics)}</div>
            <p class="blog-index__excerpt">{html.escape(p.meta["title"])}</p>
          </li>"""
        for p in papers
    )
    lead = (
        "<p>Неофициальные переводы научных статей по машинному обучению. "
        "Переводы машинные, со сверкой по скрипту.</p>"
    )
    article = f"""      <article class="tl_article">
        {lead}
        <ul class="blog-index">{items}
        </ul>
      </article>"""
    return shell(
        "Papers | ml-papers", "Переводы научных статей по машинному обучению.", article, depth=0
    )


def render_article(p: Paper) -> str:
    note_md, body_md = split_note(p.body_md)
    note = pandoc_html(note_md) if note_md else ""
    body = decorate(pandoc_html(body_md))
    doi = p.meta.get("doi", "")
    links = ['<a href="../">Все переводы</a>']
    if doi:
        links.append(f'<a href="https://doi.org/{html.escape(doi)}">Оригинал</a>')
    if p.has_pdf:
        links.append('<a href="index.pdf">PDF</a>')
    links.append(f'<a href="{REPO_URL}/blob/main/papers/{p.slug}/index.md">Markdown</a>')
    sep = f'<span class="meta-sep" aria-hidden="true">{META_SEP.strip()}</span>'
    info = [
        html.escape(p.authors),
        f"{html.escape(str(p.meta.get('journal', '')))}, {p.meta.get('year', '')}",
    ]
    if p.topics:
        info.append(
            META_SEP.join(f'<span class="topic-chip">{html.escape(t)}</span>' for t in p.topics)
        )
    meta_line = (
        "".join(f"<span>{x}</span>" for x in info)
        + f'<span class="meta-links">{sep.join(links)}</span>'
    )
    article = f"""      <article class="tl_article tl_article--post tl_article--paper">
        <h1>{html.escape(p.title_ru)}</h1>
        <address>{meta_line}</address>
        {note}
        {body}
      </article>"""
    return shell(f"{p.title_ru} | {SITE_TITLE}", p.meta["title"], article, depth=1)


def search_index(papers: list[Paper]) -> list[dict]:
    return [
        {
            "slug": p.slug,
            "title_ru": p.title_ru,
            "title": p.meta.get("title", ""),
            "authors": p.authors,
            "year": p.meta.get("year", ""),
            "topics": p.topics,
        }
        for p in papers
    ]


def build(root: Path, out: Path) -> list[str]:
    shutil.rmtree(out, ignore_errors=True)
    (out / "static").mkdir(parents=True)
    for name in ("pages.css", "paper.css", "site.js"):
        shutil.copy(root / "site-assets" / name, out / "static" / name)
    papers = load_papers(root)
    (out / "static" / "search.json").write_text(
        json.dumps(search_index(papers), ensure_ascii=False, indent=1) + "\n",
        encoding="utf-8",
    )
    (out / "index.html").write_text(render_index(papers), encoding="utf-8")
    (out / ".nojekyll").write_text("", encoding="utf-8")
    for p in papers:
        d = out / p.slug
        d.mkdir()
        (d / "index.html").write_text(render_article(p), encoding="utf-8")
        if p.has_pdf:
            shutil.copy(root / "papers" / p.slug / "index.pdf", d / "index.pdf")
        assets = root / "papers" / p.slug / "assets"
        if assets.is_dir():
            shutil.copytree(assets, d / "assets")
    return [p.slug for p in papers]


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if len(args) > 1:
        print(__doc__, file=sys.stderr)
        return 2
    root = Path(default_root())
    out = Path(args[0]) if args else root / "site"
    slugs = build(root, out)
    print(f"built {len(slugs)} paper(s) into {out}: {', '.join(slugs)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
