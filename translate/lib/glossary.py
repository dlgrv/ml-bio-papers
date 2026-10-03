"""Glossary: glossary/README.md is the human source of truth; terms.json is the runtime cache.

- `parse` / `load`: Markdown table or terms.json -> `Term` objects.
- `terms_for`: terms occurring in an English text (whole word, plural -s/-es allowed).
- `prompt_block`: only the matched terms, for the translation prompt (first-use EN paren).
- `missing`: matched terms whose Russian form is absent from the translation (inflection-safe
  prefix match), used by the verify gate.
"""

from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path

from translate.lib.config import default_root

ROW_RE = re.compile(r"^\|(.+)\|\s*$")
PAREN_RE = re.compile(r"^(?P<main>.*?)\s*\((?P<paren>[^)]*)\)\s*$")
WORD_RE = re.compile(r"[\w-]+")
EDITORIAL_NEVER_RE = re.compile(r"не\s+переводить|не\s+расшифровывать", re.IGNORECASE)
FIRST_USE_NOTE_RE = re.compile(r"при\s+первом\s+употреблении", re.IGNORECASE)


@dataclass(frozen=True)
class Term:
    label: str  # first table cell as written, e.g. "lowest common ancestor (LCA)"
    en: tuple[str, ...]  # main form first, then the abbreviation / expansion
    ru: tuple[str, ...]  # accepted Russian forms (parentheticals dropped)
    ru_raw: str
    note: str  # translator/editorial only; never injected into article text
    ru_stems: tuple[str, ...] = ()  # stem() of each word in each ru alternative
    gloss: str = ""  # reader-facing definition; first use only
    paren_en: str = "first"  # "first" | "never"

    def to_dict(self) -> dict:
        return {
            "label": self.label,
            "en": list(self.en),
            "ru": list(self.ru),
            "ru_raw": self.ru_raw,
            "note": self.note,
            "ru_stems": list(self.ru_stems),
            "gloss": self.gloss,
            "paren_en": self.paren_en,
        }

    @classmethod
    def from_dict(cls, data: dict) -> Term:
        ru = tuple(data["ru"])
        stems = data.get("ru_stems")
        return cls(
            label=data["label"],
            en=tuple(data["en"]),
            ru=ru,
            ru_raw=data["ru_raw"],
            note=data.get("note", ""),
            ru_stems=tuple(stems) if stems is not None else _ru_stems(ru),
            gloss=data.get("gloss", ""),
            paren_en=data.get("paren_en", "first"),
        )


def _norm(text: str) -> str:
    return re.sub(r"-{2,}", "-", text.replace("*", ""))


def stem(word: str) -> str:
    """Prefix used for inflection-tolerant Russian matching."""
    w = word.lower()
    if len(w) >= 5:
        return w[:-2]
    if len(w) == 4:
        return w[:-1]
    return w


def _ru_stems(ru: tuple[str, ...]) -> tuple[str, ...]:
    return tuple(stem(w) for alt in ru for w in WORD_RE.findall(alt))


def _split_en(cell: str) -> tuple[str, ...]:
    m = PAREN_RE.match(cell)
    if not m or not m["main"]:
        return (cell.strip(),)
    return (m["main"].strip(), m["paren"].strip())


def _split_ru(cell: str) -> tuple[str, ...]:
    alts = (re.sub(r"\s*\([^)]*\)", "", alt).strip() for alt in cell.split(","))
    return tuple(alt for alt in alts if alt)


def _classify_note(note: str) -> tuple[str, str, str]:
    """Split Примечание into (gloss, note, paren_en)."""
    note = note.strip()
    if not note:
        return "", "", "first"
    if EDITORIAL_NEVER_RE.search(note):
        return "", note, "never"
    if FIRST_USE_NOTE_RE.search(note):
        return "", note, "first"
    if note.startswith("не ") or "не «" in note:
        return "", note, "first"
    return note, "", "first"


def has_upper_abbr(term: Term) -> bool:
    return any(a.isupper() for a in term.en[1:])


def needs_en_paren(term: Term) -> bool:
    """True when first use should include `(english)` (not abbrev / never terms)."""
    return term.paren_en == "first" and not has_upper_abbr(term)


def first_mention_form(term: Term) -> str:
    """Suggested first-use surface form for the translation prompt."""
    if not needs_en_paren(term):
        return term.ru_raw
    base = term.ru[0] if term.ru else term.ru_raw
    if term.gloss:
        return f"{base} ({term.en[0]}; {term.gloss})"
    return f"{base} ({term.en[0]})"


def en_paren_re(en: str) -> re.Pattern[str]:
    """Match `(en)` or `(en; optional gloss)` in Russian text."""
    return re.compile(rf"\(\s*{re.escape(en)}(?:\s*;[^)]*)?\s*\)", re.IGNORECASE)


def parse(markdown: str) -> list[Term]:
    terms = []
    for line in markdown.splitlines():
        m = ROW_RE.match(line)
        if not m:
            continue
        cells = [c.strip() for c in m.group(1).split("|")]
        if len(cells) < 2 or cells[0] in {"Термин", ""} or set(cells[0]) <= {"-", ":"}:
            continue
        gloss, note, paren_en = _classify_note(cells[2] if len(cells) > 2 else "")
        ru = _split_ru(cells[1])
        terms.append(
            Term(
                cells[0],
                _split_en(cells[0]),
                ru,
                cells[1],
                note,
                _ru_stems(ru),
                gloss=gloss,
                paren_en=paren_en,
            )
        )
    return terms


def load(root: str | None = None) -> list[Term]:
    base = Path(root or default_root()) / "glossary"
    terms_json = base / "terms.json"
    if terms_json.is_file():
        data = json.loads(terms_json.read_text(encoding="utf-8"))
        return [Term.from_dict(row) for row in data]
    print(
        f"WARN: {terms_json} missing; falling back to glossary/README.md",
        file=sys.stderr,
    )
    return parse((base / "README.md").read_text(encoding="utf-8"))


def _en_re(alt: str) -> re.Pattern:
    return re.compile(rf"(?<!\w){re.escape(alt)}(?:s|es)?(?!\w)", re.IGNORECASE)


def terms_for(text: str, terms: list[Term]) -> list[Term]:
    """Terms found in `text`, in order of first occurrence; longest alternative wins on overlap."""
    clean = _norm(text)
    cands = sorted(((alt, t) for t in terms for alt in t.en), key=lambda x: -len(x[0]))
    taken: list[tuple[int, int]] = []
    found: dict[str, tuple[int, Term]] = {}
    for alt, term in cands:
        for m in _en_re(alt).finditer(clean):
            if any(m.start() < e and s < m.end() for s, e in taken):
                continue
            taken.append((m.start(), m.end()))
            if term.label not in found or m.start() < found[term.label][0]:
                found[term.label] = (m.start(), term)
    return [t for _, t in sorted(found.values(), key=lambda x: x[0])]


def ru_present(alt: str, translation: str) -> bool:
    words = [w.lower() for w in WORD_RE.findall(_norm(translation))]
    return all(any(w.startswith(stem(a)) for w in words) for a in WORD_RE.findall(alt))


def missing(
    source: str, translation: str, terms: list[Term], exceptions: set[str] | frozenset = frozenset()
) -> list[Term]:
    out = []
    for term in terms_for(source, terms):
        if term.en[0] in exceptions:
            continue
        abbr_kept = any(
            a.isupper() and re.search(rf"\b{re.escape(a)}\b", translation) for a in term.en[1:]
        )
        if not abbr_kept and not any(ru_present(alt, translation) for alt in term.ru):
            out.append(term)
    return out


def prompt_block(
    matched: list[Term], *, introduced: frozenset[str] | set[str] = frozenset()
) -> str:
    lines = []
    for t in matched:
        if t.label not in introduced and needs_en_paren(t):
            lines.append(f"{t.label} → {first_mention_form(t)}")
        else:
            lines.append(f"{t.label} → {t.ru_raw}")
    return "\n".join(lines)
