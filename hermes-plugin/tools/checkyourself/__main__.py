"""Allow ``python -m tools.checkyourself`` alongside the legacy script path."""

from .cli import main

if __name__ == "__main__":
    raise SystemExit(main())
