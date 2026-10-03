#!/usr/bin/env python3
"""Emit a human/agent review pack (no second LLM): side-by-side EN/RU + MQM checklist.

Writes translate/runs/<slug>/review.md from units.json, translated.json, and verify warnings.
Usage: python -m translate.ops.review_pack <slug>
"""

from __future__ import annotations

import sys
from collections import defaultdict
from typing import TYPE_CHECKING

from translate.lib import config, mask
from translate.lib import glossary as gl
from translate.lib.jsonio import read_json
from translate.lib.paths import work_dir
from translate.steps.verify import verify_paper as vp

if TYPE_CHECKING:
    from pathlib import Path


MQM_SECTIONS = (
    ("Accuracy", "Meaning preserved; no additions, omissions, or swapped claims."),
    (
        "Terminology",
        "Glossary forms used; first mention has (english) [+ gloss]; abbreviations once then short.",
    ),
    ("Fluency", "Natural academic Russian; no calques or broken syntax."),
    ("Hedging", "Modality matches source (may ≠ does; suggests ≠ shows)."),
    ("Numbers", "All figures, units, DOIs, and citations match the source."),
)


def _en_text(unit: dict) -> str:
    return unit.get("source_md") or mask.unmask(unit["text"], unit.get("spans") or {}, strict=False)


def _ru_text(unit: dict, results: dict) -> str:
    if not unit.get("translate", True):
        return unit.get("fixed_ru") or _en_text(unit)
    row = results.get(unit["id"]) or {}
    return row.get("text") or "_(missing translation)_"


def _glossary_hits(en: str, terms: list[gl.Term]) -> list[str]:
    return [f"{t.label} → {t.ru_raw}" for t in gl.terms_for(en, terms)]


def _collect_issues(
    slug: str, units: list, results: dict, terms: list[gl.Term], root: str | None
) -> list[vp.Issue]:
    wd = work_dir(slug, root)
    if (wd / "body.en.md").is_file() and (wd / "body.ru.md").is_file():
        return vp.verify(slug, root)
    issues: list[vp.Issue] = []
    exceptions = read_json(wd / "exceptions.json", {})
    try:
        rules = config.load_rules(root)
    except FileNotFoundError:
        rules = {}
    ru = {k: v["text"] for k, v in results.items() if v.get("status") == "ok"}
    for u in units:
        if u.get("translate") and u["id"] in ru:
            issues += vp.check_unit(
                u, ru[u["id"]], terms, rules, frozenset(exceptions.get(u["id"], []))
            )
        elif u.get("translate") and results.get(u["id"], {}).get("status") not in (None, "ok"):
            issues.append(vp.Issue(u["id"], "status", "FAIL", "needs repair"))
    return issues


def render(slug: str, root: str | None = None) -> str:
    wd = work_dir(slug, root)
    units = read_json(wd / "units.json", [])
    results = read_json(wd / "translated.json", {})
    terms = gl.load(root)
    issues = _collect_issues(slug, units, results, terms, root)
    by_unit: dict[str, list[vp.Issue]] = defaultdict(list)
    for i in issues:
        by_unit[i.unit].append(i)

    lines = [
        f"# Review pack: {slug}",
        "",
        "Advisory only — scripted `verify` remains the gate. Fill the MQM checklist below.",
        "",
        "## Units",
        "",
    ]
    for u in units:
        uid = u["id"]
        en = _en_text(u)
        ru = _ru_text(u, results)
        hits = _glossary_hits(en, terms)
        unit_issues = by_unit.get(uid, [])
        lines += [
            f"### {uid} ({u.get('kind', '?')})",
            "",
            "**EN**",
            "",
            en or "_(empty)_",
            "",
            "**RU**",
            "",
            ru,
            "",
            "**Glossary hits**",
            "",
        ]
        if hits:
            lines.extend(f"- {h}" for h in hits)
        else:
            lines.append("- _(none)_")
        lines += ["", "**Verify warnings**", ""]
        if unit_issues:
            lines.extend(f"- {i.severity} `{i.check}`: {i.message}" for i in unit_issues)
        else:
            lines.append("- _(none)_")
        lines.append("")

    paper_issues = [i for i in issues if i.unit == "-"]
    if paper_issues:
        lines += ["## Paper-level verify", ""]
        lines.extend(f"- {i.severity} `{i.check}`: {i.message}" for i in paper_issues)
        lines.append("")

    lines += ["## MQM checklist", ""]
    for title, hint in MQM_SECTIONS:
        lines += [
            f"### {title}",
            "",
            f"_{hint}_",
            "",
            "- [ ] Critical issues: _(none / list)_",
            "- [ ] Major issues: _(none / list)_",
            "- [ ] Minor notes: _(none / list)_",
            "",
        ]

    lines += [
        "## Issues for repair",
        "",
        "List unit IDs and fixes (feeds `fix_unit` / re-verify):",
        "",
        "1. ",
        "",
    ]
    return "\n".join(lines)


def write(slug: str, root: str | None = None) -> Path:
    wd = work_dir(slug, root)
    wd.mkdir(parents=True, exist_ok=True)
    path = wd / "review.md"
    path.write_text(render(slug, root), encoding="utf-8")
    return path


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if len(args) != 1:
        print(__doc__, file=sys.stderr)
        return 2
    path = write(args[0])
    print(f"wrote {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
