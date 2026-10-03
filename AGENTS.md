# Agent conventions

## Pipeline

- Map: [translate/README.md](translate/README.md). Entry: `make help`.
- **Setup (required):** `python3 -m venv .venv && .venv/bin/pip install -r requirements-dev.txt && make hooks`
- Hooks are mandatory: pre-commit runs `make lint` (ruff + yamllint + shellcheck); pre-push runs `make ci` (lint + test). Never `--no-verify`.
- Before asking to push: `make ci` must be green. Needs Python ≥3.11, pandoc (site/PDF), `shellcheck` on PATH.
- Ask the user before every `git commit`.

## Commit messages

English Conventional Commits only — enforced by `.githooks/commit-msg` and CI.

Format: `type(optional-scope): description`

| Rule | Detail |
|------|--------|
| Language | English only (no Cyrillic / CJK in subject or body) |
| Types | `feat` `fix` `docs` `chore` `ci` `test` `refactor` `sync` `translation` `quality` |
| Scope | optional, lowercase `[a-z0-9._/-]+` (e.g. `pipeline`, `verify`, `2019-kraken2`) |
| Description | imperative, starts with lowercase letter/digit, no trailing period, subject ≤72 chars |
| Body | optional; blank line after subject |
| Forbidden | Cursor/AI attribution trailers |
| Allowed | `Merge …`, `Revert "…"` |

Examples:

```
feat(pipeline): download PMC figure assets into papers assets
fix(verify): compare URL and DOI order left to right
translation(ru): Kraken 2 (2019)
test(pipeline): mutation recall for the verify gate
ci: enforce English conventional commit messages
```

Local: `make hooks` once after clone; `make check-commit-msg MSG='fix: restore templates'`.

## Git

- Branch + PR + squash to `main`. No direct pushes to `main`.
- Run `make ci` before asking to commit or push (same gate as pre-push).
