"""Canonical paths for one paper: papers/<slug>/ (published) and translate/runs/<slug>/ (work)."""

from __future__ import annotations

import re
from pathlib import Path

from translate.lib.config import default_root

SLUG_RE = re.compile(r"^\d{4}-[a-z0-9]+(?:-[a-z0-9]+)*$")


def check_slug(slug: str) -> str:
    if not SLUG_RE.fullmatch(slug):
        raise ValueError(f"bad slug {slug!r}: expected YYYY-name, e.g. 2019-kraken2")
    return slug


def _root(root: str | None) -> Path:
    return Path(root or default_root())


def paper_dir(slug: str, root: str | None = None) -> Path:
    return _root(root) / "papers" / check_slug(slug)


def index_md(slug: str, root: str | None = None) -> Path:
    return paper_dir(slug, root) / "index.md"


def meta_yml(slug: str, root: str | None = None) -> Path:
    return paper_dir(slug, root) / "meta.yml"


def assets_dir(slug: str, root: str | None = None) -> Path:
    return paper_dir(slug, root) / "assets"


def work_dir(slug: str, root: str | None = None) -> Path:
    return _root(root) / "translate" / "runs" / check_slug(slug)


def source_xml(slug: str, root: str | None = None) -> Path:
    return work_dir(slug, root) / "source.xml"
