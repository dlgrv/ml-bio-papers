#!/usr/bin/env python3
"""Publish a verified translation: papers/<slug>/index.md (with the mandatory header) and index.pdf.

Usage: build_paper.py <slug>
Needs pandoc on PATH and the typst Python package. Refuses to publish while verify reports FAIL.
"""

from __future__ import annotations

import shutil
import subprocess
import sys

import typst
import yaml

from translate.lib.paths import index_md, meta_yml, work_dir
from translate.steps.verify import verify_paper as vp

PREAMBLE = """#set page(paper: "a4", margin: (x: 18mm, y: 20mm), numbering: "1")
#set text(font: ("Helvetica Neue", "Arial", "Liberation Sans"), size: 10.5pt, lang: "ru")
#set par(justify: true, leading: 0.65em)
#set heading(numbering: none)
#show heading.where(level: 1): set text(size: 18pt)
#show heading.where(level: 2): set text(size: 13.5pt)
#show quote: set text(size: 9pt)
#show link: set text(fill: rgb("#1a4f8b"))
"""


def header(meta: dict) -> str:
    """Minimal attribution note above the translated body."""
    authors = ", ".join(meta["authors"])
    doi = (meta.get("doi") or "").strip()
    pdf = (meta.get("pdf") or meta.get("url") or "").strip()
    if doi:
        loc = f"DOI: [{doi}](https://doi.org/{doi})"
    elif pdf:
        loc = f"PDF: [{pdf}]({pdf})"
    else:
        loc = "Источник: см. meta.yml"
    return (
        f"> **Неофициальный перевод.** Оригинал: {authors}. «{meta['title']}». "
        f"{meta['journal']}, {meta['year']}. "
        f"{loc}. Лицензия: {meta['license']}.\n\n"
    )


def build(slug: str, *, force: bool = False) -> int:
    issues = vp.verify(slug)
    if vp.exit_code(issues) == 1 and not force:
        print(f"{slug}: verify has FAIL, not publishing", file=sys.stderr)
        return 1
    for tool in ("pandoc",):
        if shutil.which(tool) is None:
            print(f"{tool} not found on PATH", file=sys.stderr)
            return 1
    meta = yaml.safe_load(meta_yml(slug).read_text(encoding="utf-8"))
    body = (work_dir(slug) / "body.ru.md").read_text(encoding="utf-8")
    title, _, rest = body.partition("\n")
    out = index_md(slug)
    out.write_text(f"{title}\n\n{header(meta)}{rest.lstrip()}", encoding="utf-8")
    typ = out.with_suffix(".typ")
    try:
        subprocess.run(
            [
                "pandoc",
                str(out),
                "-f",
                "markdown+tex_math_dollars+pipe_tables",
                "-t",
                "typst",
                "-o",
                str(typ),
            ],
            check=True,
        )
        typ.write_text(PREAMBLE + typ.read_text(encoding="utf-8"), encoding="utf-8")
        typst.compile(str(typ), output=str(out.with_suffix(".pdf")))
    finally:
        typ.unlink(missing_ok=True)
    print(f"{slug}: wrote {out} and {out.with_suffix('.pdf')}")
    return 0


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if len(args) != 1:
        print(__doc__, file=sys.stderr)
        return 2
    return build(args[0])


if __name__ == "__main__":
    raise SystemExit(main())
