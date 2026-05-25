# Potassium — Makefile
# Usage: make [target]
# Requires: uv (pip install uv) + make (winget install GnuWin32.Make or use Git Bash)

.PHONY: all install check run run-full push clean

# ── Default target ──────────────────────────────────────────────────────────

all: check run push

# ── Setup ───────────────────────────────────────────────────────────────────

install:
	uv sync
	uv run playwright install chromium

# ── Type check ──────────────────────────────────────────────────────────────

check:
	uv run basedpyright main.py daily_farming.py core/ config/ platforms/

# ── Run farming ─────────────────────────────────────────────────────────────

run:
	uv run python daily_farming.py --quick

run-full:
	uv run python daily_farming.py

# ── Git push ────────────────────────────────────────────────────────────────

push:
	@if [ -z "$$(git status --porcelain)" ]; then \
		echo "Nothing to commit."; \
	else \
		git add -A; \
		git commit -m "auto: daily farming run"; \
	fi
	git push origin main

# ── Clean runtime artifacts ─────────────────────────────────────────────────

clean:
	rm -rf evidence/ profiles/*.json
	find . -type d -name "__pycache__" -exec rm -rf {} +
