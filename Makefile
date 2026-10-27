# PALATE — developer shortcuts (all Python stdlib, no dependencies)
PY ?= python3

.PHONY: help run demo test smoke clean

help:
	@echo "PALATE — targets:"
	@echo "  make run     start the web app on http://127.0.0.1:8000 (mock or live per env)"
	@echo "  make demo    start on DEMO_PORT (default 8000)"
	@echo "  make test    run the unittest suite"
	@echo "  make smoke   full proof: tests + CLI + HTTP API + live-mode guard"
	@echo "  make clean   remove __pycache__"
	@echo ""
	@echo "Live mode: export QLOO_API_KEY=... (see RUNBOOK.md / .env.example)"

run:
	$(PY) app.py

demo:
	$(PY) app.py --port $${DEMO_PORT:-8000}

test:
	$(PY) -m unittest discover -s tests -v

smoke:
	bash scripts/smoke.sh

clean:
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
