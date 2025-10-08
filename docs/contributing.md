# Contributing Guide

We welcome contributions! This document covers environment setup, testing, code style, and the pull request process.

## Table of Contents

1. [Project Setup](#project-setup)
2. [Running Tests](#running-tests)
3. [Code Style](#code-style)
4. [Pull Request Process](#pull-request-process)

## Project Setup

```bash
git clone https://github.com/hilt-format/hilt-python.git
cd hilt-python
poetry install --with dev
```

Activate the poetry shell (optional):

```bash
poetry shell
```

## Running Tests

- Unit tests: `poetry run pytest`
- Single file: `poetry run pytest tests/test_session.py`
- Coverage HTML: `poetry run pytest --cov=hilt`

Integration tests requiring extras:

```bash
poetry install -E parquet -E langchain
poetry run pytest tests/test_integration.py
```

## Code Style

- Formatting: `poetry run black .`
- Linting: `poetry run ruff check .`
- Type checking: `poetry run mypy .`

Please ensure no lint/type regressions before opening a PR.

## Pull Request Process

1. Branch from `main` (e.g., `feature/langchain-metrics`).
2. Implement changes with tests/docs as needed.
3. Run the full test suite and linters.
4. Update CHANGELOG or docs when relevant.
5. Submit the PR with a clear summary and checklist of verification steps.
6. Address review feedback promptly.

Thank you for helping grow the HILT ecosystem! 🚀
