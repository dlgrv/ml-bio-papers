#!/usr/bin/env python3
"""Show per-paper pipeline state from meta.yml + translate/runs/<slug>/state.json.

Usage: python -m translate.ops.status
"""

from __future__ import annotations

import sys
from pathlib import Path

import yaml

from translate.lib.config import default_root
from translate.lib.jsonio import read_json
from translate.lib.paths import SLUG_RE, work_dir


def collect(root: str | None = None) -> list[dict]:
    base = Path(root or default_root())
    papers = base / "papers"
    rows: list[dict] = []
    if not papers.is_dir():
        return rows
    for d in sorted(papers.iterdir()):
        if not d.is_dir() or not SLUG_RE.fullmatch(d.name):
            continue
        meta_path = d / "meta.yml"
        meta = {}
        if meta_path.exists():
            meta = yaml.safe_load(meta_path.read_text(encoding="utf-8")) or {}
        state = read_json(work_dir(d.name, root) / "state.json", {})
        rows.append(
            {
                "slug": d.name,
                "status": meta.get("status", "not-started"),
                "last_step": state.get("last_step", "-"),
                "exit_code": state.get("exit_code", "-"),
            }
        )
    return rows


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if args:
        print(__doc__, file=sys.stderr)
        return 2
    rows = collect()
    if not rows:
        print("(no papers)")
        return 0
    print(f"{'slug':<24} {'status':<22} {'last_step':<14} exit")
    for r in rows:
        print(f"{r['slug']:<24} {r['status']:<22} {r['last_step']:<14} {r['exit_code']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
