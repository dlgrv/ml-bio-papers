#!/usr/bin/env python3
"""Build glossary/terms.json from the human-edited glossary/README.md table.

Usage: python -m translate.ops.glossary_build [root]
"""

from __future__ import annotations

import sys
from pathlib import Path

from translate.lib import glossary as gl
from translate.lib.config import default_root
from translate.lib.jsonio import write_json


def build(root: str | None = None) -> Path:
    base = Path(root or default_root()) / "glossary"
    terms = gl.parse((base / "README.md").read_text(encoding="utf-8"))
    out = base / "terms.json"
    write_json(out, [t.to_dict() for t in terms])
    return out


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    root = args[0] if args else None
    path = build(root)
    print(f"wrote {path} ({len(gl.load(root))} terms)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
