# AGENTS.md

## Project

Storygram is a local-first, file-based archive for life stories. `PRD.md` is the product source of truth; `PLAN.md` lists milestone history. The long-term direction is a more user-friendly and agent-friendly system, but the core must stay deterministic and usable offline without an LLM.

Current state: the repository is an early MVP scaffold, not a finished product. Verify behavior before documenting a command as working.

## Commands

Run from the repository root; tests use relative paths such as `schema/episode.schema.json`.

```bash
pip install -e ".[dev]"
PYTHONPATH=/data/src python -m pytest -v
PYTHONPATH=/data/src python -m pytest tests/unit/test_schemas.py::test_episode_schema_valid -v
PYTHONPATH=/data/src python -m storygram --help
ruff check src tests
ruff format src tests
mypy src
```

- Prefer `PYTHONPATH=/data/src python -m storygram ...` until the package is installed.
- On Alpine or externally managed Python, install with `pip install --break-system-packages -e ".[dev]"`.
- There is no CI, pre-commit, or `uv` config despite PRD suggestions; `pyproject.toml` uses Hatchling and pip.
- Some sandboxes lack `python`/`git` on `PATH`; check before running checks and never claim a check passed unless it ran.

## Repository map

- `src/storygram/`: `cli.py`, `models.py`, `validate.py`, `index.py`, `gitcheck.py`, `bitemporal.py`, `conflicts.py`, `export.py`, `timeline.py`, `genogram.py`.
- `schema/`: canonical JSON Schemas. Root-level `*.schema.json` files are identical duplicates; update `schema/` and keep duplicates in sync or remove them deliberately.
- `data/`: canonical records (`data/<type>/`). Currently empty; sample records are only in `tests/fixtures/` and `inbox/`.
- `tests/`: unit, integration, and synthetic fixtures. Tests do not exercise most CLI commands.
- `generated/`, `inbox/`, `proposals/`, `media-manifest/` are gitignored except `.gitkeep`; do not commit derived output or unreviewed imports.
- `archive/`, `{src/`, and `session-ses_*.md` are leftover artifacts, not part of the application source.

## CLI status and quirks

- `cli.py` defines several commands twice (stubs first, real implementations later). Click keeps the last registration, so edit the later definition; deduplicate when touching it.
- Not implemented or only partial: `get` and `list` are stubs returning empty output; `ingest` only copies a file to `inbox/`; `rebuild` only builds `generated/index.db`; timeline, genogram, conflicts, and export are minimal.
- `validate` checks only `data/episodes/` and `data/assertions/`; it does not validate `inbox/`, `proposals/`, other record types, or broken references. `validate.validate_referential_integrity()` exists but is not called by the CLI.
- `init` copies only the Episode and Assertion schemas. When adding a type, update `schema/`, the init copy list, models, and tests together.
- Search reads `data/` only and builds the SQLite index on demand; `rebuild` does not regenerate views beyond the index.

## Domain invariants

These are non-negotiable (details in `PRD.md`):

- An Episode is a capture, not a fact. Ingestion must never auto-confirm an assertion.
- Keep `valid_time` (represented time) separate from `transaction_time` (recorded time). Corrections create new IDs and supersede; never overwrite history.
- Preserve conflicts explicitly with both sides and evidence; never auto-resolve.
- Archive or supersede records; never silently delete or merge people/entities.
- Keep the core deterministic and LLM-free. Future AI must submit reviewable proposals, not mutate canonical data.
- Use synthetic data only in tests and fixtures.

## Testing and docs

- A passing suite does not prove the CLI works; add or run focused CLI tests for command changes.
- Add regression tests for fixed defects and malformed/empty/boundary cases. Do not weaken tests to pass.
- Documentation is bilingual: keep `README.md` / `README.it.md`, `CONTRIBUTING.md` / `CONTRIBUTING.it.md`, and `docs/en/` / `docs/it/` in sync. `README.it.md` is the maintained Italian README; `README_ITALIANO.md` is an older duplicate.

## Git conventions

- `main` is stable; `develop` is integration; feature work uses `feature/*`.
- Use Conventional Commits (`feat:`, `fix:`, `docs:`, `test:`, `refactor:`, `chore:`, `ci:`).
- Milestone tags follow `v0.1.0-mX`; release tag is `v0.1.0`.
- Do not commit secrets, real personal data, `generated/` output, or unreviewed `inbox/` files.

## Completion report

End significant work units with:

```text
## Summary
- ...

## Files changed
- ...

## Checks run
- `command`: result

## Assumptions
- ...

## Risks or limitations
- ...

## Next step
- ...
```

When instructions conflict, prioritize safety, privacy, and data integrity over convenience. `PRD.md` is the product authority; `AGENTS.md` is the workflow authority.
