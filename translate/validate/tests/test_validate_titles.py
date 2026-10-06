"""Tests for translate/ops/validate_titles.py."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import yaml

from translate.ops.validate_titles import validate_titles

REPO_ROOT = Path(__file__).resolve().parents[3]


def _write_paper(root: Path, slug: str, meta: dict, index: str | None) -> None:
    d = root / "papers" / slug
    d.mkdir(parents=True)
    (d / "meta.yml").write_text(yaml.safe_dump(meta), encoding="utf-8")
    if index is not None:
        (d / "index.md").write_text(index, encoding="utf-8")


def test_valid_title(tmp_path):
    _write_paper(
        tmp_path,
        "2019-a",
        {"title": "A", "status": "machine-translated"},
        "# Real title\n\n## Аннотация\n\nText.\n",
    )
    assert validate_titles(tmp_path) == []


def test_not_started_without_index_ok(tmp_path):
    _write_paper(tmp_path, "2019-a", {"title": "A", "status": "not-started"}, None)
    assert validate_titles(tmp_path) == []


def test_published_missing_index(tmp_path):
    _write_paper(tmp_path, "2019-a", {"title": "A", "status": "machine-translated"}, None)
    errors = validate_titles(tmp_path)
    assert any("missing index.md" in e for e in errors)


def test_h2_abstract_as_only_heading(tmp_path):
    _write_paper(
        tmp_path,
        "2019-a",
        {"title": "A", "status": "machine-translated"},
        "## Аннотация\n\nText.\n",
    )
    errors = validate_titles(tmp_path)
    assert any("no level-1 title" in e for e in errors)


def test_h1_is_annotation_rejected(tmp_path):
    _write_paper(
        tmp_path,
        "2019-a",
        {"title": "A", "status": "machine-translated"},
        "# Аннотация\n\nText.\n",
    )
    errors = validate_titles(tmp_path)
    assert any("section name" in e for e in errors)


def test_markup_in_title_rejected(tmp_path):
    _write_paper(
        tmp_path,
        "2019-a",
        {"title": "A", "status": "machine-translated"},
        "# **BERT**: name\n\n## Аннотация\n",
    )
    errors = validate_titles(tmp_path)
    assert any("markdown markup" in e for e in errors)


def test_starts_with_h2_before_h1(tmp_path):
    _write_paper(
        tmp_path,
        "2019-a",
        {"title": "A", "status": "machine-translated"},
        "## Аннотация\n\n# Real title\n",
    )
    errors = validate_titles(tmp_path)
    assert any("starts with an H2" in e for e in errors)


def test_repo_titles_pass():
    assert validate_titles(REPO_ROOT) == []


def test_cli_fails_on_bad_title(tmp_path):
    _write_paper(
        tmp_path,
        "2019-a",
        {"title": "A", "status": "machine-translated"},
        "## Аннотация\n",
    )
    r = subprocess.run(
        [sys.executable, "-m", "translate.ops.validate_titles", str(tmp_path)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert r.returncode == 1
