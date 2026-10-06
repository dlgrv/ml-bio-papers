#!/usr/bin/env python3
"""Validate papers/*/index.md has a real level-1 title (not Abstract/Аннотация).

Exit 0 = pass, 1 = fail. Usage:
  python -m translate.ops.validate_titles [root]
"""

from __future__ import annotations

import sys
from pathlib import Path

import yaml

from translate.lib.config import default_root

# First-line H1 must not be a section label that used to leak into page titles.
_SECTION_TITLES = frozenset(
    {
        "abstract",
        "аннотация",
        "summary",
        "резюме",
        "introduction",
        "введение",
        "references",
        "список литературы",
    }
)
_UNPUBLISHED = "not-started"


def _h1_lines(md: str) -> list[str]:
    return [ln for ln in md.splitlines() if ln.startswith("# ") and not ln.startswith("##")]


def validate_titles(root: Path) -> list[str]:
    """Return error strings; empty means OK."""
    papers = root / "papers"
    if not papers.is_dir():
        return []

    errors: list[str] = []
    for d in sorted(p for p in papers.iterdir() if p.is_dir()):
        meta_path = d / "meta.yml"
        index_path = d / "index.md"
        if not meta_path.exists():
            continue
        meta = yaml.safe_load(meta_path.read_text(encoding="utf-8")) or {}
        slug = d.name
        status = meta.get("status", _UNPUBLISHED)
        if status == _UNPUBLISHED:
            continue
        if not index_path.exists():
            errors.append(f"{slug}: status {status!r} but missing index.md")
            continue
        md = index_path.read_text(encoding="utf-8")
        h1s = _h1_lines(md)
        if not h1s:
            errors.append(f"{slug}: index.md has no level-1 title (# …)")
            continue
        if len(h1s) > 1:
            errors.append(f"{slug}: index.md has {len(h1s)} level-1 titles; expected one")
        title = h1s[0][2:].strip()
        if not title:
            errors.append(f"{slug}: empty level-1 title")
            continue
        if title.lower() in _SECTION_TITLES:
            errors.append(f"{slug}: level-1 title looks like a section name ({title!r})")
        if "**" in title or "`" in title:
            errors.append(f"{slug}: level-1 title still has markdown markup ({title!r})")
        # Prefer title as the first non-empty line (after optional BOM/blank).
        for ln in md.splitlines():
            if not ln.strip():
                continue
            if ln.startswith("##"):
                errors.append(f"{slug}: index.md starts with an H2 before any H1")
            break
    return errors


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if len(args) > 1:
        print(__doc__, file=sys.stderr)
        return 2
    root = Path(args[0]) if args else Path(default_root())
    try:
        errors = validate_titles(root)
    except (OSError, ValueError, yaml.YAMLError) as e:
        print(f"ERROR: title validation failed: {e}", file=sys.stderr)
        return 1
    if errors:
        print("ERROR: title validation failed:", file=sys.stderr)
        for e in errors:
            print(f"  - {e}", file=sys.stderr)
        print(
            "\nEach published paper needs one `# Title` line in index.md "
            "(not `## Аннотация` / Abstract).",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
