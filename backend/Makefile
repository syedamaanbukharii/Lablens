.PHONY: install dev test lint run clean
install: ; pip install -e .
dev: ; pip install -e ".[dev]"
test: ; pytest --cov=lablens -q
lint: ; ruff check src tests
run: ; uvicorn lablens.api.main:app --reload
clean: ; rm -rf .pytest_cache .ruff_cache *.db uploads && find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
