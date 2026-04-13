.PHONY: install install-dev test lint format typecheck run-scaffold clean

install:
	python -m pip install -e .

install-dev:
	python -m pip install -e ".[dev]"

test:
	python -m pytest tests/ -q

lint:
	python -m ruff check .

format:
	python -m ruff format .

typecheck:
	python -m mypy .

run-scaffold:
	python -m app.main

clean:
	rm -rf build dist *.egg-info .pytest_cache .mypy_cache .ruff_cache
