# Translation conventions (TRANSLATION.md)

Unified conventions for all translations in this repository.

## Per-paper pipeline

```bash
make hooks                              # once per clone
make paper SLUG=2019-kraken2            # full run (needs LLM server + network for PMC)
make verify SLUG=2019-kraken2
make review SLUG=2019-kraken2           # advisory MQM pack
make status
make site
```

Steps: `fetch → digest → assets → translate → render → verify → repair → verify_final → publish → site`.

Details: [translate/README.md](translate/README.md).

1. Fetch JATS from PMC (`meta.yml` → `pmcid`).
2. Digest into units; download figure binaries into `papers/<slug>/assets/`.
3. MT translation (glossary from `glossary/` is mandatory).
4. Scripted verification (structure, numbers, DOI/URLs in document order, citations, figures, glossary).
5. Automated repair ≤2 rounds/unit; then `fix_unit` / human or driving agent.
6. `make review` → MQM checklist (advisory); apply fixes; re-verify.
7. Publish header + PDF; update README tables; optional Zenodo DOI.

## Pilot and reading order

Pilot: **Kraken 2** (2019). Reading order: NCBI Taxonomy (10 min) → Kraken 2 → MetaPhlAn4 → PLOS comparison → Taxometer → Perseus → YACHT.

## Do not translate (byte-identical from the source)

- DOI, URL, author names, software names (Kraken2, MetaPhlAn4, Taxometer, Perseus, YACHT, Bracken, MMSeqs2, Centrifuge, Metabuli, sourmash).
- **All numbers and units** — character for character. Decimal point stays `.` (`66.6%`, not `66,6%`).
- Dataset names (CAMI2, Rhizosphere) and databases (NCBI Taxonomy, GTDB).

## Glossary

See `glossary/` — one term, one translation across papers. First use: Russian + `(english)` and optional reader gloss; later Russian only (abbreviations: full + `(ABBR)` once). Add new terms in the same PR that introduces them. Runtime reads `glossary/terms.json` (`make glossary-build` from `glossary/README.md`).

## Required header

Minimal attribution only (no PMC/`assets/` notes, no MT status):

```markdown
> **Неофициальный перевод.** Оригинал: {authors}. «{title}». {journal}, {year}. DOI: [{doi}](https://doi.org/{doi}). Лицензия: {license}.
```

## Topics

Every `papers/<slug>/meta.yml` must set `topics` from the allowlist in [`topics.yml`](topics.yml). Prefer a focused set (about four or fewer); more is allowed when genuinely needed. Add a new topic to `topics.yml` in the same PR that first uses it.

## Difficulty

Every `papers/<slug>/meta.yml` must set `difficulty` to an integer **1–10** (how hard the paper is to read for a typical ML student). Optional `difficulty_note` is a short Russian remark without the «Сложность N/10.» prefix — the site builds that string. Score by length, math/engineering density, and prerequisites (same spirit as the [DeepPavlov course list](https://github.com/deeppavlov/agentic-course-itmo/blob/main/papers.md)). `make lint` rejects missing or out-of-range values.

## Titles

Published `papers/<slug>/index.md` must start with one level-1 `# …` title (the paper name), not `## Аннотация` / Abstract. Do not leave markdown bold/code wrappers (`**…**`, `` `…` ``) in that line — the site shows titles as plain text. `make lint` rejects missing or section-like H1s.

## Style

- Readability over calque.
- Scripted verify is the only gate; review pack is advisory.
