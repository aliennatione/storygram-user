# Current State

Last updated: 2026-10-30

## Git

- Branch: `feature/agent-proposal-flow`
- Last committed baseline: `cf6cf94 docs: clarify repo-specific agent guidance`
- Proposal engine, CLI and local web UI are implemented and tested locally.

## Environment

- Alpine Linux 3.24.2, running as root in the container.
- Repository at `/data`, bind-mounted from the host.
- Web UI will be served on `0.0.0.0:8080`; port 8080 is mapped to the host.
- Python 3.14.10, Git 2.54.0, pip 26.1.2.
- Dependencies installed with `pip install --break-system-packages -e '.[dev]'`.
- Tests use paths relative to `/data` and must be run from the repository root.

## Completed

- Repository inventory covering all 15 record types.
- `AGENTS.md` rewritten and committed.
- `src/storygram/registry.py`: central type registry, directories, prefixes, metadata allowlists, supersede/archive/evidence policies.
- `src/storygram/validate.py`: validates all record types, duplicate IDs, missing references, with `FormatChecker`.
- `schema/proposal.schema.json` v1 with explicit operations and conditional shapes; root duplicate kept in sync.
- `schema/assertion.schema.json`: corrected supersession rule. A superseded assertion must now close `transaction_time.recorded_until`; it no longer incorrectly requires `supersedes` on the old record.
- `src/storygram/proposals.py`: proposal discovery, planning, dry-run, evidence checks, metadata policy, supersession, archive, conflict blocking, atomic writes, rollback, Git commit, rejection.
- `tests/integration/test_proposal_engine.py`: engine coverage for dry-run, apply, metadata policy, supersession, unmodelled/modelled conflicts, evidence, archive policy, Git commit, dirty tree and rejection.
- `src/storygram/cli.py` rewritten without duplicate registrations.
  - `init` creates every registry directory and copies all 15 schemas.
  - `get` and `list` are real registry-backed commands.
  - `git-check` is registered once.
  - `proposal new|list|show|approve|reject` implemented.
  - `approve` supports `--dry-run`, `--no-commit` and scoped Git commits.
- `tests/integration/test_cli_proposals.py`: CLI coverage for init, proposal lifecycle, dry-run, no-commit, commit, reject and invalid input.
- `src/storygram/web.py`: stdlib HTTP UI with home, proposal list, JSON create form, dry-run preview, approve (commit/no-commit) and reject.
- `src/storygram/cli.py`: `web` command serving the UI on `0.0.0.0:8080` by default.
- `tests/integration/test_web.py`: HTTP tests for home, create, preview, approve, reject and invalid JSON.
- Documentation audit added in `docs/dev/AUDIT.md`.

## Active

- Next milestone: Playwright end-to-end tests against the real web server.
- Then the provider-agnostic LLM adapter.

## Next Steps

1. Install Playwright and Chromium, then add a smoke test for home and a full create -> preview -> approve flow.
2. Test that the UI and CLI share identical plan errors, especially evidence and conflict errors.
3. Add the provider-agnostic LLM adapter.
   - Interface accepts source text and returns a pending Proposal only.
   - Mock provider for tests; no network in the test suite.
   - Never mutates canonical data.
4. Update bilingual README/docs for proposals, UI, adapter and local-only security assumptions.
5. Decide whether to add an edit action for pending proposals and an API surface for external agents.
6. Containerize the application and add a Compose profile that optionally starts a local Ollama service.
   - Keep the default image usable without Ollama.
   - Expose the UI on `0.0.0.0:8080`.
   - Persist `/data` and generated state through volumes.
   - Document the Ollama profile, model selection and resource caveats.

## Checks

- `PYTHONPATH=/data/src python -m pytest -q`: `32 passed` after adding the web tests.
- `ruff check src tests`: passed.
- `ruff format --check src tests`: passed.
- `mypy src`: passed.
- `ruff check src/storygram/registry.py src/storygram/validate.py`: passed.
- `ruff check src/storygram/proposals.py tests/unit/test_schemas.py tests/integration/test_proposal_engine.py`: passed.

## Known Limitations

- The LLM adapter and Playwright tests do not exist yet.
- `apply_proposal` commit message is `feat(proposal): apply <id>`.
- The archived proposal records `applied_at`, but not the resulting commit hash, to keep the archive and data commit atomic.
- Conflict detection is deliberately conservative and year-based; it is not a complete temporal reasoner.
- Working-tree cleanliness checks tracked files only, so ignored pending proposals do not block approval.
- Pending proposals remain local and ignored by Git; only merged proposals are archived and committed.
- `export` and `ingest` still need the planned cleanup; `ingest` still only copies files.
- Playwright/browser dependencies are not installed yet.
- The web UI has no authentication and binds to `0.0.0.0`; use only in the controlled container/host mapping.
