PY ?= .venv/bin/python
SYS ?= python3 -I
RUN ?= $(lastword $(sort $(wildcard runs/*.json)))

.PHONY: help setup check test demo demo-leak demo-small gate manifest sync

help: ## List the commands
	@grep -E '^[a-z-]+:.*## ' $(MAKEFILE_LIST) | awk -F':.*## ' '{printf "  make %-12s %s\n", $$1, $$2}'

setup: ## Create .venv with the pinned dependencies (uses uv if present)
	@if command -v uv >/dev/null; then uv venv .venv --python 3.12 && uv pip install --python .venv -r requirements.txt; \
	else python3 -m venv .venv && .venv/bin/pip install -r requirements.txt; fi

check: ## Harness and evidence checks (standard library only)
	@$(SYS) tools/check.py

test: ## Unit tests (numpy tests are skipped if numpy is missing)
	@if [ -x $(PY) ]; then $(PY) -m unittest discover -s tests -t .; else $(SYS) -m unittest discover -s tests -t .; fi

demo: ## Run the weekly_risk example and write a run record
	@$(PY) examples/weekly_risk/run.py

demo-leak: ## Same, with a leak on purpose
	@$(PY) examples/weekly_risk/run.py --leak

demo-small: ## Do you need a neural network with 16 rows?
	@$(PY) examples/small_data/run.py

gate: ## Promotion gate on RUN=runs/<record>.json (latest record by default)
	@test -n "$(RUN)" || (echo 'No run records yet: run make demo first' && exit 1)
	@$(SYS) tools/gate.py $(RUN)

manifest: ## Register new raw data files (never re-hashes existing ones)
	@$(SYS) tools/manifest.py

sync: ## Link skills from .agents/skills into .claude/skills
	@$(SYS) tools/sync_skills.py
