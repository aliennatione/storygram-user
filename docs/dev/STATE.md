# Current State

Last updated: 2026-10-30

## Git

- Branch: `feature/agent-proposal-flow`
- Last committed baseline: `cf6cf94 docs: clarify repo-specific agent guidance`
- Proposal engine and proposal CLI are implemented and tested locally.

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

## Active

- Next milestone: local web UI bound to `0.0.0.0:8080`.
- Then the provider-agnostic LLM adapter and Playwright end-to-end flows.

## Next Steps

1. Build a small stdlib HTTP UI with no new runtime dependency unless a clear need appears.
   - Proposal list/detail pages.
   - Raw JSON create/edit form with server-side schema+plan validation.
   - Approve with dry-run preview, approve, reject.
   - Show validation and conflict errors clearly.
2. Reuse `proposals.plan_apply()` for previews so UI and CLI cannot drift.
3. Bind the server to `0.0.0.0:8080`; document local-only security assumptions.
4. Add UI tests, then Playwright smoke/flow tests.
5. Add an adapter that turns source text or an external agent response into a pending proposal only.
6. Update bilingual README/docs for the proposal and UI workflows.

## Checks

- `PYTHONPATH=/data/src python -m pytest -q`: `29 passed` after adding the CLI proposal tests.
- `ruff check src/storygram/registry.py src/storygram/validate.py`: passed.
- `ruff check src/storygram/proposals.py tests/unit/test_schemas.py tests/integration/test_proposal_engine.py`: passed.
- Full-repo ruff/mypy debt remains pre-existing and must not be presented as clean.

## Known Limitations

- The web UI and LLM adapter do not exist yet.
- `apply_proposal` commit message is `feat(proposal): apply <id>`.
- The archived proposal records `applied_at`, but not the resulting commit hash, to keep the archive and data commit atomic.
- Conflict detection is deliberately conservative and year-based; it is not a complete temporal reasoner.
- Working-tree cleanliness checks tracked files only, so ignored pending proposals do not block approval.
- Pending proposals remain local and ignored by Git; only merged proposals are archived and committed.
- `export` and `ingest` still need the planned cleanup; `ingest` still only copies files.
- Full Playwright/browser dependencies are not installed yet.
