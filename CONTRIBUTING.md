# Contributing to Storygram

## Setup
```bash
pip install --break-system-packages -e ".[dev]"
```

## Development
- Run tests: `PYTHONPATH=/data/src python -m pytest -v`
- Lint: `ruff check src tests`
- Format: `ruff format src tests`
- Type check: `mypy src`

## Git workflow
We use [Conventional Commits](https://www.conventionalcommits.org/):
- `feat:` new feature
- `fix:` bug fix
- `docs:` documentation
- `test:` tests
- `refactor:` refactoring
- `chore:` maintenance
- `ci:` CI changes

Create feature branches from `develop`, open PRs to `develop`. Keep commits atomic.
