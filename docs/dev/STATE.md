# Current State

Last updated: 2026-10-30

## Git

- Branch: `feature/agent-proposal-flow`
- Latest commit: `9e56f2d feat(web): generate pending proposals with Ollama`
- Web generation, container files and bilingual docs are committed.
- Proposal engine, CLI, local web UI, Playwright e2e tests, LLM adapter and container files are present. Python and browser checks pass locally; Docker itself was not run in this session.

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
- `src/storygram/web.py`: stdlib HTTP UI with home, proposal list, JSON create form, Ollama Generate page, dry-run preview, approve (commit/no-commit) and reject.
- `src/storygram/cli.py`: `web` command serving the UI on `0.0.0.0:8080` by default.
- `tests/integration/test_web.py`: HTTP tests for home, create, preview, approve, reject, invalid JSON, Ollama generation, empty source and provider errors.
- Web generation uses an injectable provider factory for tests; production uses `OllamaProvider` with form/env model and URL.
- Documentation audit added in `docs/dev/AUDIT.md`.
- `tests/e2e/web.mjs`: Playwright browser flow against the real server: home, create, preview, approve without commit, reject.
- `package.json` / `package-lock.json`: Playwright Node dependency and `npm run test:e2e`.
- `.gitignore`: `node_modules/` ignored.
- `src/storygram/llm.py`: provider-agnostic adapter, callable mock provider, stdlib Ollama provider, prompt builder, JSON extraction, normalization, pending-only save.
- Adapter always forces `type=Proposal`, `status=proposed` and fresh timestamps; unknown model fields are dropped.
- `proposal generate`: CLI command using local Ollama; supports `--file`, `--text`, `--model`, `--ollama-url`, `--no-save`, `--json`, `$STORYGRAM_OLLAMA_MODEL`, `$STORYGRAM_OLLAMA_URL`.
- `tests/integration/test_llm_adapter.py`: generation, fenced JSON, unknown-field removal, pending-only writes, duplicate rejection, invalid/empty input, Ollama request shape.
- `tests/integration/test_cli_proposals.py`: CLI generation saves pending only, `--no-save` writes nothing, and `init` honors `$STORYGRAM_SCHEMA_DIR`.
- Schema lookup now supports archive-local schemas, `$STORYGRAM_SCHEMA_DIR`, repository/package paths and the current directory. This fixes packaged/container `init`.
- `Dockerfile`: multi-stage Python 3.12 Alpine image, non-root user, Git plus tini, schemas copied to `/app/schema`, healthcheck on port 8080.
- `docker-entrypoint.sh`: optional auto-init of `/data` and Git, initial schema commit, Git safe-directory config, then exec the CLI.
- `compose.yaml`: persistent `storygram-data`, port 8080, optional `llm` profile with Ollama and persistent models.
- `.dockerignore`: excludes repository-local data, generated output, caches, tests and development artifacts.
- Bilingual README/docs rewritten around proposals, UI, adapter, tests and container usage; proposal contract lives in `docs/en/` and `docs/it/`.
- Packaged wheel was built, installed in a temporary venv and exercised via `storygram init` with `$STORYGRAM_SCHEMA_DIR`.

## Active

- Session ready for export/handoff. No uncommitted application work.
- Docker image/Compose runtime verification remains for a Docker-capable host.

## Next Steps

1. Build and smoke-test the Dockerfile/Compose on a Docker-capable host; verify named-volume ownership, auto-init, healthcheck and optional Ollama profile.
2. Decide whether to add pending-proposal editing and an external agent API.
3. Clean up leftover `export`/`ingest` stubs and refresh `PRD.md`/`PLAN.md` if they should describe the shipped workflow.

## Checks

- `PYTHONPATH=/data/src python -m pytest -q`: `45 passed`.
- `npm run test:e2e`: Playwright approve and reject flows passed.
- `ruff check src tests`: passed.
- `ruff format --check src tests`: passed.
- `mypy src`: passed.
- `python -m pip wheel --no-deps .`: passed; installed wheel initializes an archive with 15 schemas.
- `sh -n docker-entrypoint.sh`: passed.
- Entrypoint smoke test outside Docker: fresh archive, Git init, initial schema commit, idempotent second run.
- `compose.yaml` parsed with PyYAML; Docker runtime not tested.

## Known Limitations

- The adapter CLI requires a running Ollama server; the test suite uses a callable mock and never needs network.
- Docker artifacts were syntax-checked and parsed but not built or run in this session.
- `apply_proposal` commit message is `feat(proposal): apply <id>`.
- The archived proposal records `applied_at`, but not the resulting commit hash, to keep the archive and data commit atomic.
- Conflict detection is deliberately conservative and year-based; it is not a complete temporal reasoner.
- Working-tree cleanliness checks tracked files only, so ignored pending proposals do not block approval.
- Pending proposals remain local and ignored by Git; only merged proposals are archived and committed.
- `export` and `ingest` still need the planned cleanup; `ingest` still only copies files.
- Browser testing on Alpine uses Node Playwright with system Chromium; Python Playwright wheels are not musllinux-compatible.
- The web UI has no authentication and binds to `0.0.0.0`; use only in the controlled container/host mapping.
