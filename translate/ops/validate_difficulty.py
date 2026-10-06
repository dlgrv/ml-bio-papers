#!/usr/bin/env python3
"""Validate papers/*/meta.yml difficulty (1–10) and optional difficulty_note.

Exit 0 = pass, 1 = fail. Usage:
  python -m translate.ops.validate_difficulty [root]
"""

from __future__ import annotations

import sys
from pathlib import Path

import yaml

from translate.lib.config import default_root


def validate_difficulty(root: Path) -> list[str]:
    """Return error strings; empty means OK."""
    papers = root / "papers"
    if not papers.is_dir():
        return []

    errors: list[str] = []
    for d in sorted(p for p in papers.iterdir() if p.is_dir()):
        meta_path = d / "meta.yml"
        if not meta_path.exists():
            continue
        meta = yaml.safe_load(meta_path.read_text(encoding="utf-8")) or {}
        slug = d.name
        if "difficulty" not in meta:
            errors.append(f"{slug}: missing required field 'difficulty'")
            continue
        difficulty = meta["difficulty"]
        if isinstance(difficulty, bool) or not isinstance(difficulty, int):
            errors.append(f"{slug}: 'difficulty' must be an integer 1–10")
            continue
        if not 1 <= difficulty <= 10:
            errors.append(f"{slug}: 'difficulty' must be an integer 1–10 (got {difficulty})")

        if "difficulty_note" not in meta:
            continue
        note = meta["difficulty_note"]
        if note is None or note == "":
            continue
        if not isinstance(note, str):
            errors.append(f"{slug}: 'difficulty_note' must be a string")
            continue
        if not note.strip():
            errors.append(f"{slug}: 'difficulty_note' must be non-empty when set")
    return errors


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if len(args) > 1:
        print(__doc__, file=sys.stderr)
        return 2
    root = Path(args[0]) if args else Path(default_root())
    try:
        errors = validate_difficulty(root)
    except (OSError, ValueError, yaml.YAMLError) as e:
        print(f"ERROR: difficulty validation failed: {e}", file=sys.stderr)
        return 1
    if errors:
        print("ERROR: difficulty validation failed:", file=sys.stderr)
        for e in errors:
            print(f"  - {e}", file=sys.stderr)
        print(
            "\nAdd difficulty 1–10 to each papers/*/meta.yml, e.g.\n"
            "  difficulty: 8\n"
            '  difficulty_note: "Статья понятная, но большая."',
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
