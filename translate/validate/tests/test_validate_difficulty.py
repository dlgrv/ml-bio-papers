"""Tests for translate/ops/validate_difficulty.py."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import yaml

from translate.ops.validate_difficulty import validate_difficulty

REPO_ROOT = Path(__file__).resolve().parents[3]


def _write_paper(root: Path, slug: str, meta: dict) -> None:
    d = root / "papers" / slug
    d.mkdir(parents=True)
    (d / "meta.yml").write_text(yaml.safe_dump(meta), encoding="utf-8")


def test_valid_difficulty_and_note(tmp_path):
    _write_paper(tmp_path, "2019-a", {"title": "A", "difficulty": 8, "difficulty_note": "Note."})
    _write_paper(tmp_path, "2020-b", {"title": "B", "difficulty": 5})
    assert validate_difficulty(tmp_path) == []


def test_empty_string_note_ok(tmp_path):
    _write_paper(tmp_path, "2019-a", {"title": "A", "difficulty": 6, "difficulty_note": ""})
    assert validate_difficulty(tmp_path) == []


def test_missing_difficulty(tmp_path):
    _write_paper(tmp_path, "2019-a", {"title": "A"})
    errors = validate_difficulty(tmp_path)
    assert any("missing required field 'difficulty'" in e for e in errors)


def test_out_of_range(tmp_path):
    _write_paper(tmp_path, "2019-a", {"title": "A", "difficulty": 11})
    errors = validate_difficulty(tmp_path)
    assert any("1–10" in e for e in errors)


def test_zero_rejected(tmp_path):
    _write_paper(tmp_path, "2019-a", {"title": "A", "difficulty": 0})
    errors = validate_difficulty(tmp_path)
    assert any("1–10" in e for e in errors)


def test_bool_rejected(tmp_path):
    _write_paper(tmp_path, "2019-a", {"title": "A", "difficulty": True})
    errors = validate_difficulty(tmp_path)
    assert any("integer" in e for e in errors)


def test_non_string_note(tmp_path):
    _write_paper(tmp_path, "2019-a", {"title": "A", "difficulty": 5, "difficulty_note": 1})
    errors = validate_difficulty(tmp_path)
    assert any("difficulty_note" in e for e in errors)


def test_whitespace_only_note(tmp_path):
    _write_paper(tmp_path, "2019-a", {"title": "A", "difficulty": 5, "difficulty_note": "   "})
    errors = validate_difficulty(tmp_path)
    assert any("non-empty" in e for e in errors)


def test_no_papers_dir(tmp_path):
    assert validate_difficulty(tmp_path) == []


def test_cli_fails_on_bad_meta(tmp_path):
    _write_paper(tmp_path, "2019-a", {"title": "A", "difficulty": 99})
    r = subprocess.run(
        [sys.executable, "-m", "translate.ops.validate_difficulty", str(tmp_path)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert r.returncode == 1
