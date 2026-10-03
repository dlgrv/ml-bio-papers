#!/usr/bin/env python3
"""Translate units one by one with the local MT model (resumable).

Reads translate/runs/<slug>/units.json, writes translate/runs/<slug>/translated.json:
{unit_id: {"status": "ok"|"needs_repair", "text": "...", "error": "..."}}

Usage: translate_units.py <slug>
"""

from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import TYPE_CHECKING

from translate.lib import glossary as gl
from translate.lib import mask
from translate.lib.config import default_root
from translate.lib.jsonio import read_json, write_json
from translate.lib.paths import work_dir
from translate.llm.client import LLMError, chat

if TYPE_CHECKING:
    from collections.abc import Callable

PROMPT = Path(default_root()) / "translate" / "prompts" / "translate-unit.md"
SENT_RE = re.compile(r"(?<=[.!?])\s+")
CONTEXT_SENTENCES = 2
MAX_TOKENS = 4096


def plain(unit: dict) -> str:
    """Source text with placeholders restored: what a human reads, what the glossary matches on."""
    return mask.unmask(unit["text"], unit["spans"], strict=False)


def _abbrevs(unit: dict, terms: list[gl.Term]) -> set[str]:
    out = set()
    for term in gl.terms_for(plain(unit), terms):
        for alt in term.en[1:]:
            if alt.isupper() or re.fullmatch(r"[A-Z][A-Za-z0-9]{1,6}", alt):
                out.add(alt)
    return out


def abbrev_state(units: list[dict], terms: list[gl.Term], upto: int) -> set[str]:
    """Abbreviations already introduced by the translatable units before index `upto` (source order)."""
    seen: set[str] = set()
    for u in units[:upto]:
        if u["translate"]:
            seen |= _abbrevs(u, terms)
    return seen


def _paren_en_terms(unit: dict, terms: list[gl.Term]) -> list[gl.Term]:
    return [t for t in gl.terms_for(plain(unit), terms) if gl.needs_en_paren(t)]


def first_mention_state(units: list[dict], terms: list[gl.Term], upto: int) -> set[str]:
    """Term labels already given an EN paren by units before index `upto`."""
    seen: set[str] = set()
    for u in units[:upto]:
        if u["translate"]:
            seen |= {t.label for t in _paren_en_terms(u, terms)}
    return seen


def _context(units: list[dict], index: int) -> str:
    for u in reversed(units[:index]):
        if u["translate"] and u["kind"] in {"para", "figure", "supplementary"}:
            return " ".join(
                SENT_RE.split(mask.unmask(u["text"], u["spans"]).strip())[-CONTEXT_SENTENCES:]
            )
    return ""


def _user_message(unit: dict, units: list[dict], index: int, terms: list[gl.Term]) -> str:
    parts = []
    matched = gl.terms_for(plain(unit), terms)
    introduced = first_mention_state(units, terms, index)
    block = gl.prompt_block(matched, introduced=introduced)
    if block:
        parts.append(f"Glossary:\n{block}")
    here = _abbrevs(unit, terms)
    seen = abbrev_state(units, terms, index)
    first = sorted(here - seen)
    known = sorted(here & seen)
    notes = []
    if first:
        notes.append("first use: " + ", ".join(first))
    if known:
        notes.append("already introduced: " + ", ".join(known))
    if notes:
        parts.append("Abbreviation notes: " + "; ".join(notes))
    here_fm = {t.en[0] for t in _paren_en_terms(unit, terms)}
    seen_fm: set[str] = set()
    for u in units[:index]:
        if u["translate"]:
            seen_fm |= {t.en[0] for t in _paren_en_terms(u, terms)}
    fm_first = sorted(here_fm - seen_fm)
    fm_known = sorted(here_fm & seen_fm)
    fm_notes = []
    if fm_first:
        fm_notes.append("first use: " + ", ".join(fm_first))
    if fm_known:
        fm_notes.append("already introduced: " + ", ".join(fm_known))
    if fm_notes:
        parts.append("First-mention notes: " + "; ".join(fm_notes))
    ctx = _context(units, index)
    if ctx:
        parts.append(f"Context (do not translate): {ctx}")
    parts.append(f"Text:\n{unit['text']}")
    return "\n\n".join(parts)


def translate_units(
    units: list[dict],
    llm: Callable[..., str],
    terms: list[gl.Term],
    out_path: Path,
    *,
    retries: int = 2,
    prompt: str | None = None,
) -> dict:
    system = (prompt if prompt is not None else PROMPT.read_text(encoding="utf-8")).strip()
    results: dict = read_json(out_path, {})
    for index, unit in enumerate(units):
        if not unit["translate"] or results.get(unit["id"], {}).get("status") == "ok":
            continue
        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": _user_message(unit, units, index, terms)},
        ]
        results[unit["id"]] = _translate_one(unit, llm, messages, retries)
        write_json(out_path, results)
    return results


def _translate_one(unit: dict, llm: Callable[..., str], messages: list[dict], retries: int) -> dict:
    draft, error = "", ""
    for _attempt in range(retries + 1):
        try:
            draft = llm(messages, max_tokens=MAX_TOKENS)
            mask.check_placeholders(draft, unit["text"])
        except (LLMError, mask.PlaceholderError) as e:
            error = str(e)
            if isinstance(e, mask.PlaceholderError):
                messages = [
                    *messages[:2],
                    {"role": "assistant", "content": draft},
                    {
                        "role": "user",
                        "content": f"Defect: {error}. Output the corrected translation only.",
                    },
                ]
            continue
        return {"status": "ok", "text": draft.strip()}
    return {"status": "needs_repair", "text": draft.strip(), "error": error}


def main(argv: list[str] | None = None) -> int:
    import json

    args = sys.argv[1:] if argv is None else argv
    if len(args) != 1:
        print(__doc__, file=sys.stderr)
        return 2
    wd = work_dir(args[0])
    units = json.loads((wd / "units.json").read_text(encoding="utf-8"))
    results = translate_units(units, chat, gl.load(), wd / "translated.json")
    bad = [k for k, v in results.items() if v["status"] != "ok"]
    total = sum(u["translate"] for u in units)
    print(f"{args[0]}: {len(results)}/{total} translated, {len(bad)} need a manual fix {bad}")
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
