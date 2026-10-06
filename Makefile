# ml-papers translation pipeline. Run from repo root.
# After clone: python3 -m venv .venv && .venv/bin/pip install -r requirements-dev.txt && make hooks
export PYTHONPATH := $(CURDIR)
PY = .venv/bin/python3
RUFF = .venv/bin/ruff

.PHONY: help test lint format ci hooks check-commit-msg glossary-build paper verify status site review

help:  ## List targets (make hooks required after clone)
	@grep -E '^[a-z-]+:.*##' $(MAKEFILE_LIST) | sed 's/:.*## /\t/'

test:  ## Unit tests (no network, no LLM server)
	$(PY) -m pytest translate -q

format:  ## Autofix Python (ruff format + check --fix)
	$(RUFF) format translate
	$(RUFF) check --fix translate

lint:  ## All linters (must match CI and pre-commit)
	$(RUFF) format --check translate
	$(RUFF) check translate
	$(PY) -m yamllint .github/workflows/ papers/*/meta.yml topics.yml
	$(PY) -m translate.ops.validate_topics
	$(PY) -m translate.ops.validate_difficulty
	shellcheck translate/steps/translate/*.sh

ci:  ## Local gate ≈ pre-push / GitHub (lint + test)
	$(MAKE) lint
	$(MAKE) test

hooks:  ## Install local git hooks (required: commit-msg, pre-commit lint, pre-push ci)
	git config core.hooksPath .githooks
	@echo "✓ core.hooksPath=.githooks (commit-msg, pre-commit lint, pre-push make ci)"

check-commit-msg:  ## Validate a message: make check-commit-msg MSG='fix: …'
	@[ -n "$(MSG)" ] || (echo "Usage: make check-commit-msg MSG='type: description'" && exit 1)
	@printf '%s\n' "$(MSG)" | $(PY) translate/ops/check_commit_msg.py --stdin

glossary-build:  ## Regenerate glossary/terms.json from glossary/README.md
	$(PY) -m translate.ops.glossary_build

paper:  ## Full pipeline for SLUG=…
	$(PY) -m translate.run $(SLUG)

verify:  ## Verify only SLUG=…
	$(PY) -m translate.steps.verify.verify_paper $(SLUG)

status:  ## Per-paper pipeline state
	$(PY) -m translate.ops.status

site:  ## Build static site into site/
	$(PY) -m translate.steps.site.build_site

review:  ## Advisory MQM pack for SLUG=… → translate/runs/<slug>/review.md
	$(PY) -m translate.ops.review_pack $(SLUG)
