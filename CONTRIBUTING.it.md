# Contribuire a Storygram

## Setup
```bash
pip install --break-system-packages -e ".[dev]"
```

## Sviluppo
- Test: `PYTHONPATH=/data/src python -m pytest -v`
- Lint: `ruff check src tests`
- Formattazione: `ruff format src tests`
- Type check: `mypy src`

## Workflow Git
Usiamo [Conventional Commits](https://www.conventionalcommits.org/):
- `feat:` nuova funzionalità
- `fix:` correzione bug
- `docs:` documentazione
- `test:` test
- `refactor:` refactoring
- `chore:` manutenzione
- `ci:` modifiche CI

Crea branch feature da `develop`, apri PR verso `develop`. Mantieni commit atomici.
