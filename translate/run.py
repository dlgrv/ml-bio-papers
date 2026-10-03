#!/usr/bin/env python3
"""One command for the whole pipeline.

Usage: python -m translate.run <slug> [--from STEP]
Steps: fetch digest assets translate render verify repair verify_final publish site.
Each step is resumable; `--from` skips earlier ones. Exit code is verify_final's
(0 clean, 1 FAIL, 2 WARN only).
"""

from __future__ import annotations

import sys
from datetime import UTC, datetime

from translate.lib.jsonio import write_json
from translate.lib.paths import work_dir
from translate.steps.digest import jats_digest
from translate.steps.fetch import fetch_assets, fetch_jats
from translate.steps.publish import build_paper
from translate.steps.render import render_md
from translate.steps.repair import repair_units
from translate.steps.site import build_site
from translate.steps.translate import translate_units
from translate.steps.verify import verify_paper

STEPS = (
    "fetch",
    "digest",
    "assets",
    "translate",
    "render",
    "verify",
    "repair",
    "verify_final",
    "publish",
    "site",
)


def plan(start: str, have_source: bool) -> list[str]:
    if start not in STEPS:
        raise ValueError(f"unknown step {start!r}, choose from {STEPS}")
    steps = list(STEPS[STEPS.index(start) :])
    if start == "fetch" and have_source and "fetch" in steps:
        steps.remove("fetch")
    return steps


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    start = "fetch"
    if "--from" in args:
        i = args.index("--from")
        start = args[i + 1]
        del args[i : i + 2]
    if len(args) != 1:
        print(__doc__, file=sys.stderr)
        return 2
    slug = args[0]
    steps = plan(start, (work_dir(slug) / "source.xml").exists())
    verify_code = 0
    skip_repair = False
    for step in steps:
        if step == "repair" and skip_repair:
            print("== repair (skipped)")
            _write_state(slug, step, 0)
            continue
        print(f"== {step}")
        code = _run_step(step, slug)
        _write_state(slug, step, code)

        if step == "verify":
            verify_code = code
            skip_repair = code in (0, 2)
            continue
        if step == "verify_final":
            verify_code = code
            if code not in (0, 2):
                return code
            continue
        if step in {"translate", "repair"}:
            continue
        if code not in (0, 2):
            return code
    return verify_code


def _run_step(step: str, slug: str) -> int:
    if step == "fetch":
        return fetch_jats.main([slug])
    if step == "digest":
        return jats_digest.main([slug])
    if step == "assets":
        return fetch_assets.main([slug])
    if step == "translate":
        return translate_units.main([slug])
    if step == "render":
        return _render(slug)
    if step in {"verify", "verify_final"}:
        return verify_paper.main([slug])
    if step == "repair":
        return repair_units.main([slug])
    if step == "publish":
        return build_paper.main([slug])
    if step == "site":
        return build_site.main([])
    raise ValueError(f"unknown step {step!r}")


def _render(slug: str) -> int:
    if not _all_ok(slug):
        print(
            "render: some units need a manual fix (python -m translate.steps.fix.fix_unit)",
            file=sys.stderr,
        )
        return 1
    return render_md.main([slug, "--original"]) or render_md.main([slug])


def _all_ok(slug: str) -> bool:
    from translate.lib.jsonio import read_json

    results = read_json(work_dir(slug) / "translated.json", {})
    return bool(results) and all(v["status"] == "ok" for v in results.values())


def _write_state(slug: str, step: str, code: int) -> None:
    write_json(
        work_dir(slug) / "state.json",
        {
            "slug": slug,
            "last_step": step,
            "exit_code": code,
            "ts": datetime.now(tz=UTC).isoformat(),
        },
    )


if __name__ == "__main__":
    raise SystemExit(main())
