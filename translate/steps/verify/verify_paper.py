#!/usr/bin/env python3
"""Verify a translated paper: per-unit and paper-level checks, no LLM involved.

Exit code: 0 clean, 1 any FAIL, 2 only WARN.
Usage: verify_paper.py <slug>   (reads units.json, translated.json, body.en.md, body.ru.md)
"""

from __future__ import annotations

import re
import sys
from collections import Counter
from dataclasses import dataclass
from typing import TYPE_CHECKING

from translate.lib import config, mask
from translate.lib import glossary as gl
from translate.lib.jsonio import read_json
from translate.lib.paths import assets_dir, work_dir

if TYPE_CHECKING:
    from pathlib import Path

NUM_RE = re.compile(r"(?<![\w.])[−-]?\d+(?:[.,]\d+)*(?:[–-]\d+(?:[.,]\d+)*)?%?")
URL_RE = re.compile(r"https?://[^\s)\]>]+")
DOI_RE = re.compile(r"doi:\s*10\.\d{4,9}/\S+")
# Left-to-right scan: URLs and DOIs in document order (not sorted, not concatenated lists).
LINK_RE = re.compile(r"https?://[^\s)\]>]+|doi:\s*10\.\d{4,9}/\S+")
IMG_ASSET_RE = re.compile(r"!\[[^\]]*\]\(assets/([^)\s]+)\)")
CITE_RE = re.compile(r"\[\d+(?:\s*[,–-]\s*\d+)*\]")
LATIN_RE = re.compile(r"[A-Za-z]{3,}")
CYR_RE = re.compile(r"[А-Яа-яЁё]")

NEG_EN = re.compile(
    r"\b(?:not|no|never|without|cannot|neither|nor|none|failed to|unable to|unless|absen\w+|lack\w*|n't)\b",
    re.IGNORECASE,
)
NEG_RU = re.compile(
    r"\b(?:не|нет|ни|без|нельзя|невозможно|никогда|никакой|никак|отсутств\w+|лишен\w*|избеж\w+|предотвращ\w+)\b",
    re.IGNORECASE,
)
HEDGE_EN = {
    "may": ("мож", "возможно", "допуска"),
    "might": ("мож", "возможно", "мог", "допуска"),
    "could": ("мож", "мог", "возможно"),
    "suggest": ("указыва", "свидетельств", "предполага", "наводит"),
    "likely": ("вероятн", "скорее", "по-видимому"),
    "appear": ("по-видимому", "кажется", "очевидно"),
    "possible": ("возможн", "можно", "нельзя", "невозможн"),
}
STRONG_RU = re.compile(
    r"\b(?:доказыва\w*|подтвержда\w*|гарантиру\w*|всегда|определённо)\b", re.IGNORECASE
)
STRONG_EN = re.compile(
    r"\b(?:prov\w+|confirm\w*|guarantee\w*|always|demonstrat\w+|ensur\w+|show\w*|establish\w*)\b",
    re.IGNORECASE,
)
SEVERITY = {"FAIL": 1, "WARN": 2}


@dataclass(frozen=True)
class Issue:
    unit: str
    check: str
    severity: str
    message: str


def _strip_ph(text: str) -> str:
    return mask.PH_RE.sub(" ", text)


NUM_WORDS = {
    **dict.fromkeys(("один", "одного", "одному", "одним", "одну", "одна", "одной", "одно"), 1),
    **dict.fromkeys(("два", "две", "двух", "двум", "обе", "оба", "обеих", "обоих", "пара"), 2),
    **dict.fromkeys(("три", "трёх", "трех", "трём"), 3),
    **dict.fromkeys(("четыре", "четырёх", "четырех"), 4),
    **dict.fromkeys(("пять", "пяти"), 5),
    **dict.fromkeys(("шесть", "шести"), 6),
    **dict.fromkeys(("семь", "семи"), 7),
    **dict.fromkeys(("восемь", "восьми"), 8),
    **dict.fromkeys(("девять", "девяти"), 9),
    **dict.fromkeys(("десять", "десяти"), 10),
}


def _norm(text: str, *, ru: bool) -> str:
    """Bring numbers to one notation: space-separated thousands match English commas; decimal point must stay a point."""
    t = re.sub(r"[\u00a0\u2009\u202f]", " ", _strip_ph(text))
    t = re.sub(r"(?<=\d) %", "%", t)
    pattern = r"(?<=\d) (?=\d{3}\b)" if ru else r"(?<=\d),(?=\d{3}\b)"
    return re.sub(pattern, "", t)


def _numbers(text: str, *, ru: bool = False) -> Counter:
    return Counter(NUM_RE.findall(_norm(text, ru=ru)))


def _check_numbers(uid: str, src: str, ru: str) -> list[Issue]:
    want, got = _numbers(src), _numbers(ru, ru=True)
    lost = Counter({n: c for n, c in want.items() if n not in got})
    words = {NUM_WORDS[w] for w in re.findall(r"[а-яё]+", ru.lower()) if w in NUM_WORDS}
    for n in list(lost):
        if n.isdigit() and int(n) in words:
            del lost[n]
    added = Counter({n: c for n, c in got.items() if n not in want})
    if lost or added:
        return [
            Issue(
                uid,
                "numbers",
                "FAIL",
                f"numbers differ: lost {sorted(lost.elements())} added {sorted(added.elements())}",
            )
        ]
    return []


def _neg_count_en(text: str) -> int:
    return len(NEG_EN.findall(_strip_ph(text)))


def _neg_count_ru(text: str) -> int:
    return len(NEG_RU.findall(_strip_ph(text)))


def _check_negation(uid: str, src: str, ru: str) -> list[Issue]:
    en_neg, ru_neg = _neg_count_en(src) > 0, _neg_count_ru(ru) > 0
    if en_neg != ru_neg:
        if en_neg:
            return [Issue(uid, "negation", "FAIL", "negation lost")]
        return [Issue(uid, "negation", "WARN", "negation added, check the meaning")]
    return []


def _check_hedging(uid: str, src: str, ru: str) -> list[Issue]:
    low, ru_low = _strip_ph(src).lower(), ru.lower()
    for word, stems in HEDGE_EN.items():
        if re.search(rf"\b{word}", low) and not any(st in ru_low for st in stems):
            return [Issue(uid, "hedging", "WARN", f"hedge '{word}' not found in translation")]
    if STRONG_RU.search(ru) and not STRONG_EN.search(low):
        return [Issue(uid, "hedging", "WARN", "translation is stronger than the source")]
    return []


def _check_untranslated(uid: str, ru: str) -> list[Issue]:
    plain = _strip_ph(ru)
    words = LATIN_RE.findall(plain)
    if len(words) >= 6 and len(CYR_RE.findall(plain)) < len(words):
        return [Issue(uid, "untranslated", "WARN", "mostly Latin text, looks untranslated")]
    return []


def _check_banned(uid: str, ru: str, rules: dict) -> list[Issue]:
    out = []
    for rule in rules.get("banned_calques", []):
        bad = rule["bad"]
        for m in re.finditer(rf"\b{re.escape(bad)}\w*", ru, re.IGNORECASE):
            tail = ru[m.end() : m.end() + 40]
            if not re.match(rf"\s*\([^)]*{re.escape(rule['good'])}", tail, re.IGNORECASE):
                out.append(
                    Issue(uid, "banned_calque", "FAIL", f"'{m.group()}' → use '{rule['good']}'")
                )
    return out


def check_unit(
    unit: dict, ru: str, terms: list[gl.Term], rules: dict | None = None, exceptions=frozenset()
) -> list[Issue]:
    src = unit["text"]
    uid = unit["id"]
    plain_src = mask.unmask(src, unit.get("spans", {}), strict=False)
    plain_ru = mask.unmask(ru, unit.get("spans", {}), strict=False)
    issues = _check_numbers(uid, src, ru)
    issues += _check_negation(uid, src, ru)
    issues += _check_hedging(uid, src, ru)
    issues += _check_untranslated(uid, ru)
    issues += [
        Issue(uid, "glossary", "FAIL", f"term missing: {t.en[0]} → {t.ru_raw}")
        for t in gl.missing(plain_src, plain_ru, terms, exceptions)
    ]
    issues += _check_banned(uid, ru, rules or {})
    return issues


def check_final_text(text: str) -> list[Issue]:
    return [
        Issue("-", "placeholder", "FAIL", f"placeholder left in output: {m}")
        for m in mask.PH_RE.findall(text)[:5]
    ]


def _expansions(unit_text: str, terms: list[gl.Term]) -> set[str]:
    return {a for t in gl.terms_for(unit_text, terms) for a in t.en[1:] if a.isupper()}


def check_paper(units: list[dict], ru: dict[str, str], terms: list[gl.Term]) -> list[Issue]:
    out = []
    tr = [u for u in units if u["translate"]]
    for kind in sorted({u["kind"] for u in tr}):
        n_src = sum(1 for u in tr if u["kind"] == kind)
        n_ru = sum(1 for u in tr if u["kind"] == kind and u["id"] in ru)
        if n_src != n_ru:
            out.append(
                Issue("-", "structure", "FAIL", f"{kind}: {n_src} in source, {n_ru} translated")
            )
    expanded: dict[str, list[str]] = {}
    forms: dict[str, set[str]] = {}
    first_en: dict[str, str] = {}  # term.label -> first unit id
    for u in tr:
        text = mask.unmask(ru.get(u["id"], ""), u["spans"], strict=False) if u["id"] in ru else ""
        for term in gl.terms_for(mask.unmask(u["text"], u["spans"], strict=False), terms):
            for alt in term.ru:
                if gl.ru_present(alt, text):
                    forms.setdefault(term.label, set()).add(alt)
                    break
            for abbr in term.en[1:]:
                if abbr.isupper() and re.search(rf"\(\s*{re.escape(abbr)}\s*\)", text):
                    expanded.setdefault(abbr, []).append(u["id"])
            if not gl.needs_en_paren(term):
                continue
            en = term.en[0]
            has_paren = bool(gl.en_paren_re(en).search(text))
            if term.label not in first_en:
                first_en[term.label] = u["id"]
                if not has_paren:
                    out.append(
                        Issue(
                            u["id"],
                            "first_mention",
                            "FAIL",
                            f"missing ({en}) on first use → {gl.first_mention_form(term)}",
                        )
                    )
                elif term.gloss and term.gloss not in text:
                    out.append(
                        Issue(
                            u["id"],
                            "gloss",
                            "WARN",
                            f"missing gloss on first use: {term.gloss}",
                        )
                    )
            elif has_paren:
                out.append(
                    Issue(
                        u["id"],
                        "first_mention",
                        "WARN",
                        f"({en}) repeated after {first_en[term.label]}",
                    )
                )
    out += [
        Issue(ids[1], "abbrev", "WARN", f"{abbr} expanded again (first at {ids[0]})")
        for abbr, ids in expanded.items()
        if len(ids) > 1
    ]
    out += [
        Issue("-", "glossary", "FAIL", f"{label}: inconsistent forms {sorted(f)}")
        for label, f in forms.items()
        if len(f) > 1
    ]
    return out


def extract_links(md: str) -> list[str]:
    return [m.group(0) for m in LINK_RE.finditer(md)]


def check_links(en_md: str, ru_md: str) -> list[Issue]:
    en, ru = extract_links(en_md), extract_links(ru_md)
    if en != ru:
        return [Issue("-", "links", "FAIL", f"URLs/DOIs differ: {en[:6]} vs {ru[:6]}")]
    return []


def check_figures(
    units: list[dict],
    en_md: str,
    ru_md: str,
    *,
    assets_path: Path | None = None,
) -> list[Issue]:
    """Require each figure graphic as markdown image in EN and RU bodies; file on disk if present."""
    issues: list[Issue] = []
    en_imgs = set(IMG_ASSET_RE.findall(en_md))
    ru_imgs = set(IMG_ASSET_RE.findall(ru_md))
    root = assets_path
    for u in units:
        if u.get("kind") != "figure":
            continue
        for name in u.get("graphics") or []:
            if name not in en_imgs:
                issues.append(
                    Issue(u["id"], "figures", "FAIL", f"missing image assets/{name} in EN")
                )
            if name not in ru_imgs:
                issues.append(
                    Issue(u["id"], "figures", "FAIL", f"missing image assets/{name} in RU")
                )
            if root is not None and not (root / name).is_file():
                issues.append(Issue(u["id"], "figures", "FAIL", f"missing file assets/{name}"))
    return issues


def check_citations(en_md: str, ru_md: str) -> list[Issue]:
    en, ru = CITE_RE.findall(en_md), CITE_RE.findall(ru_md)
    if en != ru:
        return [Issue("-", "citations", "FAIL", f"citation groups differ: {en[:6]} vs {ru[:6]}")]
    return []


def _refs_block(md: str) -> str:
    m = re.search(r"^## (?:References|Список литературы)\n+(.*)\Z", md, re.DOTALL | re.MULTILINE)
    return m.group(1).strip() if m else ""


def check_refs(en_md: str, ru_md: str) -> list[Issue]:
    if _refs_block(en_md) != _refs_block(ru_md):
        return [Issue("-", "references", "FAIL", "reference list differs from source")]
    return []


def exit_code(issues: list[Issue]) -> int:
    if any(i.severity == "FAIL" for i in issues):
        return 1
    return 2 if issues else 0


def verify(slug: str, root: str | None = None) -> list[Issue]:
    wd = work_dir(slug, root)
    units = read_json(wd / "units.json", [])
    results = read_json(wd / "translated.json", {})
    ru = {k: v["text"] for k, v in results.items() if v["status"] == "ok"}
    terms = gl.load(root)
    rules = config.load_rules(root)
    exceptions = read_json(wd / "exceptions.json", {})
    issues = [
        Issue(k, "status", "FAIL", "needs repair")
        for k, v in results.items()
        if v["status"] != "ok"
    ]
    for u in units:
        if u["translate"] and u["id"] in ru:
            issues += check_unit(
                u, ru[u["id"]], terms, rules, frozenset(exceptions.get(u["id"], []))
            )
    issues += check_paper(units, ru, terms)
    en_md = (wd / "body.en.md").read_text(encoding="utf-8")
    ru_md = (wd / "body.ru.md").read_text(encoding="utf-8")
    assets = assets_dir(slug, root)
    return (
        issues
        + check_links(en_md, ru_md)
        + check_figures(units, en_md, ru_md, assets_path=assets if assets.is_dir() else None)
        + check_citations(en_md, ru_md)
        + check_refs(en_md, ru_md)
        + check_final_text(ru_md)
    )


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if len(args) != 1:
        print(__doc__, file=sys.stderr)
        return 2
    issues = verify(args[0])
    for i in issues:
        print(f"{i.severity:4} {i.unit:5} {i.check}: {i.message}")
    print(
        f"{args[0]}: {sum(i.severity == 'FAIL' for i in issues)} FAIL, {sum(i.severity == 'WARN' for i in issues)} WARN"
    )
    return exit_code(issues)


if __name__ == "__main__":
    raise SystemExit(main())
