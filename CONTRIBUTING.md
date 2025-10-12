# Contributing to HILT

Thank you for helping improve zero-friction LLM observability. This guide explains how to set up the project, keep quality high, and propose changes with confidence.

## Development Setup

```bash
git clone https://github.com/hilt-format/hilt-python.git
cd hilt-python
poetry install --with dev
```

Activate the Poetry shell if you prefer an isolated environment:

```bash
poetry shell
```

## Quality Checklist

- Formatting: `poetry run black .`
- Linting: `poetry run ruff check .`
- Type checking: `poetry run mypy hilt`
- Tests: `poetry run pytest`
- Coverage (optional but encouraged): `poetry run pytest --cov`

Run these commands before submitting a pull request to prevent CI surprises.

## Submitting a Pull Request

1. Branch from `main` with a descriptive name (e.g., `feature/openai-metrics-tweak`).
2. Implement the change with tests or docs as needed.
3. Update relevant documentation when behaviour or APIs change.
4. Re-run the quality checklist.
5. Open the PR with:
   - A concise summary of the change
   - Verification steps (commands + outcomes)
   - Follow-up work, if any
6. Respond to review feedback quickly so the change can ship.

## Release Flow (Maintainers)

1. Update `CHANGELOG.md`.
2. Bump the version in `pyproject.toml`.
3. Run `poetry lock && poetry install` to refresh dependency locks.
4. Execute the full quality checklist.
5. Tag and publish: `git tag vX.Y.Z && git push origin vX.Y.Z --tags`.
6. GitHub Actions will build and push the release to PyPI.

We appreciate your contributions—every improvement helps teams ship reliable LLM features faster. 🚀
