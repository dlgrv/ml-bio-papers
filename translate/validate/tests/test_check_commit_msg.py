"""Tests for translate/ops/check_commit_msg.py."""

import subprocess
import sys
from pathlib import Path

from translate.ops.check_commit_msg import validate

REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT = REPO_ROOT / "translate" / "ops" / "check_commit_msg.py"


def test_good_simple():
    assert validate("fix: restore V2 editorial templates") == []


def test_good_scoped():
    assert validate("translation(ru): kraken 2 (2019)") == []


def test_good_with_body():
    msg = "feat(pipeline): add make og target\n\nRegenerate locale previews."
    assert validate(msg) == []


def test_good_breaking_bang():
    assert validate("feat(pipeline)!: rename wave output dir") == []


def test_good_sync_quality():
    assert validate("sync: pull upstream chapters 03, 08") == []
    assert validate("quality(ru): strip bureaucratese markers") == []


def test_merge_allowed():
    assert validate("Merge pull request #51 from dlgrv/quality/pipeline-v2") == []


def test_revert_allowed():
    assert validate('Revert "fix: broken redirect"') == []


def test_reject_cyrillic():
    assert any("English" in e for e in validate("feat: единый V2-дизайн OG"))


def test_reject_cjk():
    assert any("English" in e for e in validate("fix: 第 5 节加两条"))


def test_reject_bad_type():
    assert any("must match" in e for e in validate("wip: temporary stash"))


def test_reject_uppercase_desc():
    assert any("lowercase" in e for e in validate("fix: Restore templates"))


def test_reject_trailing_period():
    assert any("period" in e for e in validate("fix: restore templates."))


def test_reject_missing_blank_line():
    assert any(
        "blank line" in e
        for e in validate("fix: restore templates\nMore detail without blank line")
    )


def test_reject_cursor_trailer():
    msg = "fix: restore templates\n\nCo-authored-by: Cursor <cursoragent@cursor.com>"
    assert any("Cursor" in e for e in validate(msg))


def test_reject_empty():
    assert any("empty" in e for e in validate("   \n# comment only\n"))


def test_strip_git_comments():
    assert validate("fix: restore templates\n\n# Please enter the commit message\n") == []


def test_cli_pass():
    r = subprocess.run(
        [sys.executable, str(SCRIPT), "--stdin"],
        input="chore: ignore pipeline run state",
        text=True,
        capture_output=True,
        cwd=REPO_ROOT,
        check=False,
    )
    assert r.returncode == 0, r.stderr


def test_cli_fail():
    r = subprocess.run(
        [sys.executable, str(SCRIPT), "--stdin"],
        input="bad message without type",
        text=True,
        capture_output=True,
        cwd=REPO_ROOT,
        check=False,
    )
    assert r.returncode == 1
    assert "ERROR" in r.stderr
