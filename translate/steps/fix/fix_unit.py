#!/usr/bin/env python3
"""Manually fix one unit: store a hand-written Russian text after the placeholder check.

Usage: fix_unit.py <slug> <unit_id> <text | ->     (`-` reads the text from stdin)
Rejects text whose placeholders differ from the source, and writes nothing in that case.
"""

from __future__ import annotations

import sys

from translate.lib import mask
from translate.lib.jsonio import read_json, write_json
from translate.lib.paths import work_dir


def fix(slug: str, uid: str, text: str, root: str | None = None) -> None:
    wd = work_dir(slug, root)
    units = {u["id"]: u for u in read_json(wd / "units.json", [])}
    results = read_json(wd / "translated.json", {})
    if uid not in units:
        raise KeyError(uid)
    text = text.strip()
    mask.check_placeholders(text, units[uid]["text"])
    results[uid] = {"status": "ok", "text": text, "manual": True}
    write_json(wd / "translated.json", results)


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if len(args) != 3:
        print(__doc__, file=sys.stderr)
        return 2
    slug, uid, text = args
    try:
        fix(slug, uid, sys.stdin.read() if text == "-" else text)
    except (KeyError, mask.PlaceholderError) as e:
        print(f"{slug} {uid}: rejected: {e}", file=sys.stderr)
        return 1
    print(f"{slug} {uid}: fixed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
