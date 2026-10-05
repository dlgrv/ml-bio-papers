"""Tests for translate/ops/validate_topics.py."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import yaml

from translate.ops.validate_topics import load_allowlist, validate_topics

REPO_ROOT = Path(__file__).resolve().parents[3]


def _env() -> dict[str, str]:
    return {**os.environ, "PYTHONPATH": str(REPO_ROOT)}


def _write_paper(root: Path, slug: str, meta: dict) -> None:
    d = root / "papers" / slug
    d.mkdir(parents=True)
    (d / "meta.yml").write_text(yaml.safe_dump(meta), encoding="utf-8")


def _allowlist(root: Path, topics: list[str] | None = None) -> None:
    (root / "topics.yml").write_text(
        yaml.safe_dump({"topics": topics or ["metagenomics", "llm", "rag"]}),
        encoding="utf-8",
    )


def test_load_allowlist_from_repo():
    allowed = load_allowlist(REPO_ROOT)
    assert "metagenomics" in allowed
    assert "agents" in allowed


def test_valid_single_and_multi_topic(tmp_path):
    _allowlist(tmp_path)
    _write_paper(tmp_path, "2019-a", {"title": "A", "topics": ["metagenomics"]})
    _write_paper(tmp_path, "2020-b", {"title": "B", "topics": ["llm", "rag"]})
    assert validate_topics(tmp_path) == []


def test_missing_topics_field(tmp_path):
    _allowlist(tmp_path)
    _write_paper(tmp_path, "2019-a", {"title": "A"})
    errors = validate_topics(tmp_path)
    assert any("2019-a" in e and "missing" in e for e in errors)


def test_empty_topics_list(tmp_path):
    _allowlist(tmp_path)
    _write_paper(tmp_path, "2019-a", {"title": "A", "topics": []})
    errors = validate_topics(tmp_path)
    assert any("2019-a" in e and "empty" in e for e in errors)


def test_unknown_topic(tmp_path):
    _allowlist(tmp_path)
    _write_paper(tmp_path, "2019-a", {"title": "A", "topics": ["bio"]})
    errors = validate_topics(tmp_path)
    assert any("2019-a" in e and "unknown" in e and "bio" in e for e in errors)


def test_non_list_topics(tmp_path):
    _allowlist(tmp_path)
    _write_paper(tmp_path, "2019-a", {"title": "A", "topics": "metagenomics"})
    errors = validate_topics(tmp_path)
    assert any("2019-a" in e and "list" in e for e in errors)


def test_non_string_entry(tmp_path):
    _allowlist(tmp_path)
    _write_paper(tmp_path, "2019-a", {"title": "A", "topics": [1]})
    errors = validate_topics(tmp_path)
    assert any("2019-a" in e and "string" in e for e in errors)


def test_skips_dirs_without_meta(tmp_path):
    _allowlist(tmp_path)
    (tmp_path / "papers" / "scratch").mkdir(parents=True)
    assert validate_topics(tmp_path) == []


def test_cli_fails_on_errors(tmp_path):
    _allowlist(tmp_path)
    _write_paper(tmp_path, "2019-a", {"title": "A", "topics": ["nope"]})
    proc = subprocess.run(
        [sys.executable, "-m", "translate.ops.validate_topics", str(tmp_path)],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
        env=_env(),
    )
    assert proc.returncode == 1
    assert "unknown" in proc.stderr
