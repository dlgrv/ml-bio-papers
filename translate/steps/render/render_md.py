#!/usr/bin/env python3
"""Render units (+ translated texts) to Markdown.

Usage: render_md.py <slug> [--original]
  default: translate/runs/<slug>/translated.json -> translate/runs/<slug>/body.ru.md
  --original: the English source rendered the same way -> body.en.md (for side-by-side checks)
"""

from __future__ import annotations

import json
import sys

from translate.lib import mask
from translate.lib.paths import work_dir

RU_LABELS = {"Fig.": "Рис.", "Figure": "Рис."}


def _titles(units: list[dict], texts: dict[str, str]) -> dict[str, str]:
    """rid -> heading text, for resolving <xref ref-type=sec> to the (translated) title."""
    out = {}
    for u in units:
        if u["kind"] == "heading" and u["src_id"]:
            if u.get("fixed_ru"):
                out[u["src_id"]] = u["fixed_ru"]
            else:
                raw = texts.get(u["id"], u["text"])
                out[u["src_id"]] = mask.unmask(raw, u["spans"], strict=False)
    return out


def _body(u: dict, texts: dict[str, str], titles: dict[str, str], *, original: bool) -> str:
    if not u["translate"]:
        return u["source_md"] if original or not u.get("fixed_ru") else u["fixed_ru"]
    if original:
        return mask.unmask(u["text"], u["spans"])
    if u["id"] not in texts:
        raise KeyError(f"no translation for unit {u['id']}")
    return mask.unmask(texts[u["id"]], u["spans"], titles)


def _label(label: str, *, original: bool) -> str:
    if original:
        return label
    for en, ru in RU_LABELS.items():
        if label.startswith(en):
            return ru + label[len(en) :]
    return label


def _figure_block(u: dict, body: str, *, original: bool) -> str:
    label = _label(u["label"], original=original) if u.get("label") else ""
    parts: list[str] = []
    for name in u.get("graphics") or []:
        alt = label.rstrip(".") if label else name
        parts.append(f"![{alt}](assets/{name})")
    if label:
        parts.append(f"**{label}.** {body}")
    elif body:
        parts.append(body)
    return "\n\n".join(parts)


def render(units: list[dict], texts: dict[str, str], *, original: bool) -> str:
    titles = {} if original else _titles(units, texts)
    blocks: list[str] = []
    refs: list[str] = []
    for u in units:
        body = _body(u, texts, titles, original=original)
        kind = u["kind"]
        if kind in {"title", "heading"}:
            blocks.append(f"{'#' * u['level']} {body}")
        elif kind == "figure":
            blocks.append(_figure_block(u, body, original=original))
        elif kind == "supplementary" and u.get("label"):
            blocks.append(f"**{_label(u['label'], original=original)}.** {body}")
        elif kind == "ref":
            refs.append(body)
        else:
            blocks.append(body)
        if kind != "ref" and refs:
            blocks.append("\n".join(refs))
            refs = []
    if refs:
        blocks.append("\n".join(refs))
    return "\n\n".join(b for b in blocks if b) + "\n"


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    original = "--original" in args
    slugs = [a for a in args if not a.startswith("--")]
    if len(slugs) != 1:
        print(__doc__, file=sys.stderr)
        return 2
    wd = work_dir(slugs[0])
    units = json.loads((wd / "units.json").read_text(encoding="utf-8"))
    texts: dict[str, str] = {}
    if not original:
        texts = {
            k: v["text"]
            for k, v in json.loads((wd / "translated.json").read_text(encoding="utf-8")).items()
        }
    out = wd / ("body.en.md" if original else "body.ru.md")
    out.write_text(render(units, texts, original=original), encoding="utf-8")
    print(f"{slugs[0]}: wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
