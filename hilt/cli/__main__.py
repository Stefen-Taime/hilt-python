"""Allow running `python -m hilt.cli`."""

from .main import main

if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
