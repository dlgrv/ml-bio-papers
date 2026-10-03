"""Deterministic mutations against the verify gate (mini-fixture style).

Each mutation must produce at least one FAIL from check_unit / check_links /
check_figures / check_paper — never a reimplementation of the gate.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from translate.lib import glossary as gl
from translate.steps.verify import verify_paper as vp

if TYPE_CHECKING:
    from collections.abc import Callable

TERMS = gl.parse(
    "| Термин | Перевод | Примечание |\n|---|---|---|\n"
    "| lowest common ancestor (LCA) | наименьший общий предок | |\n"
    "| k-mer | k-мер | |\n"
)

SRC_NUMBERS = "The error was 0.95 at p < 0.001 for the lowest common ancestor."
RU_OK = "Ошибка составила 0.95 при p < 0.001 для наименьшего общего предка."


def _unit(uid: str, src: str, *, kind: str = "para") -> dict:
    return {
        "id": uid,
        "kind": kind,
        "translate": True,
        "text": src,
        "spans": {},
        "source_md": src,
    }


def _fails(issues: list[vp.Issue]) -> bool:
    return any(i.severity == "FAIL" for i in issues)


def mutate_number_changed() -> list[vp.Issue]:
    return vp.check_unit(_unit("u001", SRC_NUMBERS), RU_OK.replace("0.95", "0.59"), TERMS)


def mutate_pvalue_dropped() -> list[vp.Issue]:
    return vp.check_unit(_unit("u001", SRC_NUMBERS), RU_OK.replace("p < 0.001", "p значимо"), TERMS)


def mutate_doi_digit() -> list[vp.Issue]:
    en = "see doi:10.1093/bioinformatics/bty648 and https://example.com/a"
    ru = en.replace("10.1093", "10.1099")
    return vp.check_links(en, ru)


def mutate_missing_figure() -> list[vp.Issue]:
    units = [{"id": "u1", "kind": "figure", "graphics": ["fig1.jpg"]}]
    en = "![Fig. 1](assets/fig1.jpg)\n\n**Fig. 1.** cap"
    ru = "**Рис. 1.** подпись"
    return vp.check_figures(units, en, ru)


def mutate_decimal_comma() -> list[vp.Issue]:
    return vp.check_unit(_unit("u001", "score 0.95"), "оценка 0,95", TERMS)


def mutate_glossary_synonym() -> list[vp.Issue]:
    return vp.check_unit(_unit("u001", "the lowest common ancestor"), "общий родитель", TERMS)


MUTATIONS: list[tuple[str, Callable[[], list[vp.Issue]]]] = [
    ("number_changed", mutate_number_changed),
    ("pvalue_dropped", mutate_pvalue_dropped),
    ("doi_digit", mutate_doi_digit),
    ("missing_figure", mutate_missing_figure),
    ("decimal_comma", mutate_decimal_comma),
    ("glossary_synonym", mutate_glossary_synonym),
]


def mutation_recall() -> dict[str, bool]:
    """name → True if the verify helpers reported a FAIL for that mutation."""
    return {name: _fails(fn()) for name, fn in MUTATIONS}
