#!/usr/bin/env python3
"""Validate papers/*/meta.yml topics against topics.yml allowlist.

Exit 0 = pass, 1 = fail. Usage:
  python -m translate.ops.validate_topics [root]
"""

from __future__ import annotations

import sys
from pathlib import Path

import yaml

from translate.lib.config import default_root


def load_allowlist(root: Path) -> set[str]:
    path = root / "topics.yml"
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    topics = data.get("topics")
    if not isinstance(topics, list) or not topics:
        raise ValueError(f"{path}: expected non-empty 'topics' list")
    if not all(isinstance(t, str) and t for t in topics):
        raise ValueError(f"{path}: every topic must be a non-empty string")
    return set(topics)


def validate_topics(root: Path) -> list[str]:
    """Return error strings; empty means OK."""
    allowed = load_allowlist(root)
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
        if "topics" not in meta:
            errors.append(f"{slug}: missing required field 'topics'")
            continue
        topics = meta["topics"]
        if not isinstance(topics, list):
            errors.append(f"{slug}: 'topics' must be a list")
            continue
        if not topics:
            errors.append(f"{slug}: 'topics' must be a non-empty list")
            continue
        for i, t in enumerate(topics):
            if not isinstance(t, str) or not t:
                errors.append(f"{slug}: topics[{i}] must be a non-empty string")
                continue
            if t not in allowed:
                errors.append(f"{slug}: unknown topic {t!r} (see topics.yml)")
    return errors


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if len(args) > 1:
        print(__doc__, file=sys.stderr)
        return 2
    root = Path(args[0]) if args else Path(default_root())
    try:
        errors = validate_topics(root)
    except (OSError, ValueError, yaml.YAMLError) as e:
        print(f"ERROR: topics validation failed: {e}", file=sys.stderr)
        return 1
    if errors:
        print("ERROR: topics validation failed:", file=sys.stderr)
        for e in errors:
            print(f"  - {e}", file=sys.stderr)
        print(
            "\nAdd topics from topics.yml to each papers/*/meta.yml, e.g.\n"
            "  topics:\n"
            "    - metagenomics",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
