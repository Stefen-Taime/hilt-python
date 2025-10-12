# Contributing

We welcome improvements to HILT—whether it's expanding instrumentation coverage, refining documentation, or fixing bugs. This guide focuses on day-to-day contributor tasks.

## Environment setup

```bash
git clone https://github.com/hilt-format/hilt-python.git
cd hilt-python
poetry install --with dev
```

Enter the Poetry shell if you prefer an activated virtualenv:

```bash
poetry shell
```

## Run the checks

- Tests: `poetry run pytest`
- Lint: `poetry run ruff check .`
- Format: `poetry run black .`
- Types: `poetry run mypy hilt`

Run at least the tests before every push; run the full set when touching shared modules or instrumentation internals.

## Working on documentation

- Markdown lives in `docs/` and the project root (e.g., `README.md`).
- Keep examples consistent with the latest auto-instrumentation API (`instrument`, `uninstrument`, `Session`).
- Use fenced code blocks with language identifiers (` ```python `) for syntax highlighting.

## Pull request checklist

- Branch from `main` using a descriptive name.
- Include tests or updated docs when behaviours change.
- List verification commands in the PR description.
- Update `CHANGELOG.md` when user-visible features are added or modified.

Thanks for helping build reliable LLM observability!
