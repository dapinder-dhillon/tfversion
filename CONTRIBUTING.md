# Contributing to tfversion

## Prerequisites

- Python 3.13+
- [Poetry](https://python-poetry.org/docs/#installation)
- An AWS profile with `s3:GetObject` on a Terraform state bucket (for manual testing only)

## Dev setup

```bash
git clone https://github.com/your-org/tfversion.git
cd tfversion
poetry install
```

## Running tests

```bash
poetry run pytest -v
```

All tests are offline — no AWS credentials needed.

## Code style

- Classes over standalone functions for any non-trivial logic
- Every class and method has a single responsibility
- No docstrings, no inline comments explaining what the code does
- Each class lives in its own file under `src/tfversion/`
- Imports ordered: stdlib → third-party → local

## Submitting a pull request

1. Fork the repo and create a branch from `main`
2. Make your changes and add tests covering them
3. Confirm `poetry run pytest -v` passes with no failures
4. Open a pull request — the PR template will guide you through the checklist

## Reporting a bug

Use the [bug report template](.github/ISSUE_TEMPLATE/bug_report.yml) on the Issues tab.
For security issues, see [SECURITY.md](SECURITY.md).
