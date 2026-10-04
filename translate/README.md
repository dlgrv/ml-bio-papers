# Translation pipeline

EN→RU pipeline for scientific papers: PMC JATS → units → LLM translate → Markdown → verify → publish → site.

## Setup (required)

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements-dev.txt
make hooks                 # commit-msg + pre-commit lint + pre-push make ci
# also: pandoc, shellcheck on PATH
```

Never `--no-verify`. Local contract before push: `make ci`.

## Commands

```bash
make ci                    # lint + test (same as pre-push / CI)
make lint                  # ruff + yamllint + shellcheck
make format                # ruff format + check --fix
make paper SLUG=2019-kraken2
make verify SLUG=2019-kraken2
make status
make review SLUG=2019-kraken2   # side-by-side MQM pack → translate/runs/<slug>/review.md
make site
make glossary-build
```

Or: `python -m translate.run <slug> [--from STEP]`.

## Steps

`fetch → digest → assets → translate → render → verify → repair → verify_final → publish → site`

- **assets:** PMC figure binaries → `papers/<slug>/assets/` via `translate.lib.pmc_media` (CDN URLs from the article HTML). When PMC also links a larger original next to `*_HTML.jpg`, that raster is stored under the JATS basename. Rejects non-image payloads.
- **repair:** ≤2 automated rounds per unit, then escalate to `python -m translate.steps.fix.fix_unit <slug> <unit_id>` (human or driving agent). No endless auto-loop.
- **verify_final** sets the process exit code (0 / 1 FAIL / 2 WARN).

Work state lives in `translate/runs/<slug>/` (gitignored). Published output: `papers/<slug>/`.

## Shelf tools

Evaluated: N/A (removed in HTLB trim). Do not reintroduce without a measured signal on scientific prose.
