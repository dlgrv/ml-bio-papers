#!/usr/bin/env python3
"""Mechanical-first repair for units that fail verify; LLM only when needed.

Re-runs verify_paper.verify, tries number/DOI restore and decimal-comma→point, else
one LLM call per round (max 2 rounds/unit). Leftovers stay needs_repair with a
repair_report.json for human review via fix_unit.

Usage: python -m translate.steps.repair.repair_units <slug>
"""

from __future__ import annotations

import re
import sys
from collections import defaultdict
from pathlib import Path
from typing import TYPE_CHECKING

from translate.lib import config, mask
from translate.lib import glossary as gl
from translate.lib.config import default_root
from translate.lib.jsonio import read_json, write_json
from translate.lib.paths import work_dir
from translate.llm.client import LLMError, chat
from translate.steps.render import render_md
from translate.steps.verify import verify_paper as vp

if TYPE_CHECKING:
    from collections.abc import Callable

PROMPT = Path(default_root()) / "translate" / "prompts" / "repair-unit.md"
MAX_ROUNDS = 2
MAX_TOKENS = 4096
DEC_COMMA_RE = re.compile(r"(?<=\d),(?=\d)")
FIX_HINT = "python -m translate.steps.fix.fix_unit"


def repair_units(
    slug: str, root: str | None = None, *, llm: Callable[..., str] | None = None
) -> int:
    """Repair failing units for `slug`. Returns verify exit code after the last round."""
    client = llm or chat
    wd = work_dir(slug, root)
    units = {u["id"]: u for u in read_json(wd / "units.json", [])}
    results: dict = read_json(wd / "translated.json", {})
    report: dict = {"rounds": [], "leftover": []}
    system = PROMPT.read_text(encoding="utf-8").strip()
    terms = gl.load(root)
    rules = config.load_rules(root)

    for round_i in range(1, MAX_ROUNDS + 1):
        _rerender(wd, units, results)
        issues = vp.verify(slug, root)
        fails = [i for i in issues if i.severity == "FAIL"]
        if not fails:
            write_json(wd / "repair_report.json", report)
            return 0

        by_unit: dict[str, list[vp.Issue]] = defaultdict(list)
        paper_checks: set[str] = set()
        for issue in fails:
            if issue.unit == "-":
                paper_checks.add(issue.check)
            else:
                by_unit[issue.unit].append(issue)

        targets = set(by_unit)
        if "links" in paper_checks:
            for u in units.values():
                if not u.get("translate"):
                    continue
                ru_text = (results.get(u["id"]) or {}).get("text") or ""
                if vp.extract_links(u["text"]) != vp.extract_links(ru_text):
                    targets.add(u["id"])

        if not targets:
            report["rounds"].append({"round": round_i, "fixed": [], "failed": ["-"]})
            break

        fixed: list[str] = []
        failed: list[str] = []
        for uid in sorted(targets):
            unit = units.get(uid)
            if unit is None or not unit.get("translate", True):
                continue
            row = results.get(uid) or {"status": "needs_repair", "text": ""}
            text = row.get("text") or ""
            unit_issues = by_unit.get(uid, [])
            checks = {i.check for i in unit_issues} | paper_checks
            messages = [f"{i.check}: {i.message}" for i in unit_issues] or [
                f"{c}: paper-level" for c in sorted(paper_checks)
            ]

            candidate = _mechanical(unit, text, checks)
            if candidate is not None and _accept(unit, candidate, terms, rules):
                results[uid] = {"status": "ok", "text": candidate, "repaired": "mechanical"}
                fixed.append(uid)
                continue

            try:
                draft = _llm_repair(client, system, unit, text, messages)
                mask.check_placeholders(draft, unit["text"])
            except (LLMError, mask.PlaceholderError) as e:
                results[uid] = {"status": "needs_repair", "text": text, "error": str(e)}
                failed.append(uid)
                continue

            if _accept(unit, draft, terms, rules):
                results[uid] = {"status": "ok", "text": draft, "repaired": "llm"}
                fixed.append(uid)
            else:
                results[uid] = {
                    "status": "needs_repair",
                    "text": draft,
                    "error": "; ".join(messages),
                }
                failed.append(uid)

        write_json(wd / "translated.json", results)
        report["rounds"].append({"round": round_i, "fixed": fixed, "failed": failed})
        # Always loop again when something was fixed so verify can clear paper-level links.
        if not fixed and not failed:
            break

    _rerender(wd, units, results)
    issues = vp.verify(slug, root)
    leftover = sorted(
        {i.unit for i in issues if i.severity == "FAIL" and i.unit != "-"}
        | {k for k, v in results.items() if v.get("status") != "ok"}
    )
    for uid in leftover:
        row = results.get(uid)
        if row and row.get("status") == "ok":
            results[uid] = {
                "status": "needs_repair",
                "text": row["text"],
                "error": "still failing after repair",
            }
    report["leftover"] = leftover
    write_json(wd / "translated.json", results)
    write_json(wd / "repair_report.json", report)
    if leftover:
        print(
            f"{slug}: {len(leftover)} unit(s) still need a manual fix "
            f"({FIX_HINT} <slug> <unit_id> <text>): {leftover}",
            file=sys.stderr,
        )
    return vp.exit_code(issues)


def _mechanical(unit: dict, text: str, checks: set[str]) -> str | None:
    src = unit["text"]
    out = text
    if "numbers" in checks or DEC_COMMA_RE.search(out):
        out = _restore_numbers(src, out)
    if "links" in checks or vp.extract_links(src) != vp.extract_links(out):
        out = _restore_links(src, out)
    return out if out != text else None


def _restore_numbers(src: str, ru: str) -> str:
    text = DEC_COMMA_RE.sub(".", ru)
    spaced = mask.PH_RE.sub(lambda m: " " * len(m.group()), text)
    src_nums = vp.NUM_RE.findall(mask.PH_RE.sub(" ", src))
    matches = list(vp.NUM_RE.finditer(spaced))
    if len(matches) != len(src_nums):
        return text
    out = text
    for match, num in zip(reversed(matches), reversed(src_nums), strict=True):
        out = out[: match.start()] + num + out[match.end() :]
    return out


def _restore_links(src: str, ru: str) -> str:
    want, got = vp.extract_links(src), vp.extract_links(ru)
    if len(want) != len(got):
        return ru
    out = ru
    for w, g in zip(want, got, strict=True):
        if w != g:
            out = out.replace(g, w, 1)
    return out


def _accept(unit: dict, text: str, terms: list, rules: dict) -> bool:
    if any(i.severity == "FAIL" for i in vp.check_unit(unit, text, terms, rules)):
        return False
    return vp.extract_links(unit["text"]) == vp.extract_links(text)


def _llm_repair(
    llm: Callable[..., str],
    system: str,
    unit: dict,
    text: str,
    messages: list[str],
) -> str:
    prompt = [
        {"role": "system", "content": system},
        {
            "role": "user",
            "content": (
                f"Source:\n{unit['text']}\n\n"
                f"Translation:\n{text}\n\n"
                f"Failures:\n" + "\n".join(messages) + "\n\n"
                "Output the corrected translation only."
            ),
        },
    ]
    return llm(prompt, max_tokens=MAX_TOKENS).strip()


def _rerender(wd: Path, units: dict[str, dict], results: dict) -> None:
    ordered = list(units.values())
    texts = {k: v["text"] for k, v in results.items() if "text" in v}
    for u in ordered:
        if u["translate"] and u["id"] not in texts:
            texts[u["id"]] = u["text"]
    (wd / "body.en.md").write_text(render_md.render(ordered, {}, original=True), encoding="utf-8")
    (wd / "body.ru.md").write_text(
        render_md.render(ordered, texts, original=False), encoding="utf-8"
    )


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if len(args) != 1:
        print(__doc__, file=sys.stderr)
        return 2
    return repair_units(args[0])


if __name__ == "__main__":
    raise SystemExit(main())
