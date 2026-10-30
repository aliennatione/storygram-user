# Current State

Last updated: 2026-10-30

## Git

- Branch: `feature/agent-proposal-flow`
- Last committed baseline: `cf6cf94 docs: clarify repo-specific agent guidance`
- This work unit adds the proposal engine, proposal schema v1 and support notes.

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

## Active

- Wire proposal commands into the CLI.
- Add Python-level proposal API tests after CLI wiring.
- Next milestone is the local web UI, then the LLM adapter and Playwright flows.

## Next Steps

1. Deduplicate `cli.py` command registrations while touching it.
2. Add `proposal new`, `proposal list`, `proposal show`, `proposal approve`, `proposal reject`.
   - `approve --dry-run` plans only.
   - `approve --no-commit` writes without Git.
   - Default approve requires a clean tracked tree and creates one scoped commit.
3. Add focused CLI integration tests, including `--dry-run` and `--no-commit`.
4. Update `init` to create `data/proposals`, `data/collections` and copy all schemas.
5. Replace stub `get`/`list` with registry-backed commands.
6. Add the local web UI bound to `0.0.0.0:8080`.
7. Add a provider-agnostic LLM adapter that can only emit pending proposals.
8. Add Playwright end-to-end tests for the UI flow.

## Checks

- `PYTHONPATH=/data/src python -m pytest -q`: `24 passed` after adding the proposal engine tests.
- `ruff check src/storygram/registry.py src/storygram/validate.py`: passed.
- `ruff check src/storygram/proposals.py tests/unit/test_schemas.py tests/integration/test_proposal_engine.py`: passed.
- Full-repo ruff/mypy debt remains pre-existing and must not be presented as clean.

## Known Limitations

- Proposal CLI/UI do not exist yet.
- `apply_proposal` commit message is `feat(proposal): apply <id>`.
- The archived proposal records `applied_at`, but not the resulting commit hash, to keep the archive and data commit atomic.
- Conflict detection is deliberately conservative and year-based; it is not a complete temporal reasoner.
- Working-tree cleanliness checks tracked files only, so ignored pending proposals do not block approval.
- Pending proposals remain local and ignored by Git; only merged proposals are archived and committed.
- `init`, `export`, `get`, `list` and `ingest` still need the planned cleanup.
- Full Playwright/browser dependencies are not installed yet.
