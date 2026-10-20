PY ?= .venv/bin/python
PIP ?= .venv/bin/pip

.PHONY: venv install run test lint fmt

venv:
	python3 -m venv .venv

install: venv
	$(PIP) install -U pip
	$(PIP) install -e ".[dev]"

run:
	$(PY) -m uvicorn app.main:app --reload --port 8000

test:
	$(PY) -m pytest

lint:
	$(PY) -m ruff check .

fmt:
	$(PY) -m ruff format .
