# Contributing to HILT

Thanks for your interest in contributing! This document outlines how to set up a development environment, coding standards, and the pull request workflow.

## Setup Instructions

```bash
git clone https://github.com/hilt-format/hilt-python.git
cd hilt-python
poetry install --with dev
```

Optional: activate the Poetry shell with `poetry shell`.

## Code Standards

- **Formatting:** `poetry run black .`
- **Linting:** `poetry run ruff check .`
- **Type checking:** `poetry run mypy hilt`
- **Testing:** `poetry run pytest`
- **Coverage:** `poetry run pytest --cov`

Please ensure all commands pass before opening a pull request.

## Pull Request Template

When opening a PR, include:

- Summary of changes
- Testing performed (commands + results)
- Any follow-up work or TODOs
- Screenshot/output when relevant (CLI, docs)

## Release Checklist (Maintainers)

1. Update `CHANGELOG.md` with new entries.
2. Bump version in `pyproject.toml`.
3. Run `poetry lock && poetry install`.
4. Execute `poetry run pytest --cov` and ensure all linters pass.
5. Tag the release: `git tag vX.Y.Z && git push origin vX.Y.Z`.
6. GitHub Actions will publish to PyPI and create a release.

Happy logging! 🚀
