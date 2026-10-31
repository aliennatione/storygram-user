# Current State

Last updated: 2026-10-31

## Git

- Branch: `feature/agent-proposal-flow`
- Latest commit: `d705939 docs: record pending edit and API handoff state`
- Web generation, container files, bilingual docs, pending editing and the JSON API are implemented.
- Proposal engine, CLI, local web UI, Playwright e2e tests, LLM adapter and container files are present.
- Python, lint and browser checks pass. The container image has now been built and exercised end-to-end through the host Docker socket.
- Documentation updates for the verified container run are uncommitted; check `git status` before starting.

## Environment

- Alpine development container, running as root.
- Repository at `/data`, bind-mounted from the host.
- Python 3.14.10, Git 2.54.0, pip 26.1.2, Node 24.22.1/npm 11.12.1 and system Chromium.
- Dependencies installed with `pip install --break-system-packages -e '.[dev]'`; Docker client and Compose installed with `apk add --no-cache docker-cli docker-cli-compose`.
- Tests use paths relative to `/data` and must be run from the repository root.
- `/var/run/docker.sock` is the host socket. In this session it exposed Podman Engine 5.8.2 through its Docker-compatible API; Docker CLI was 29.9.2 and Compose v5.6.1. This is not Docker-in-Docker; never start `dockerd`.

## Completed

- Repository inventory covering all 15 record types.
- `AGENTS.md` rewritten and committed.
- `src/storygram/registry.py`: central type registry, directories, prefixes, metadata allowlists, supersede/archive/evidence policies.
- `src/storygram/validate.py`: validates all record types, duplicate IDs, missing references, with `FormatChecker`.
- `schema/proposal.schema.json` v1 with explicit operations and conditional shapes; root duplicate kept in sync.
- `schema/assertion.schema.json`: corrected supersession rule. A superseded assertion must now close `transaction_time.recorded_until`; it no longer incorrectly requires `supersedes` on the old record.
- `src/storygram/proposals.py`: proposal discovery, planning, dry-run, evidence checks, metadata policy, supersession, archive, conflict blocking, atomic writes, rollback, Git commit, rejection.
- Pending proposal helpers: `create_pending` and `update_pending`, with atomic writes, ID immutability, created_at preservation and closed/applied guards.
- `tests/integration/test_proposal_engine.py`: engine coverage for dry-run, apply, metadata policy, supersession, unmodelled/modelled conflicts, evidence, archive policy, Git commit, dirty tree and rejection.
- `src/storygram/cli.py` rewritten without duplicate registrations.
  - `init` creates every registry directory and copies all 15 schemas.
  - `get` and `list` are real registry-backed commands.
  - `git-check` is registered once.
  - `proposal new|list|show|approve|reject` implemented.
  - `approve` supports `--dry-run`, `--no-commit` and scoped Git commits.
- `tests/integration/test_cli_proposals.py`: CLI coverage for init, proposal lifecycle, dry-run, no-commit, commit, reject and invalid input.
- `src/storygram/web.py`: stdlib HTTP UI with home, proposal list, JSON create form, Ollama Generate page, pending edit page, dry-run preview, approve (commit/no-commit) and reject.
- JSON API: `GET/POST /api/proposals`, `GET/PUT /api/proposals/<id>`; no approve endpoint.
- `src/storygram/cli.py`: `web` command serving the UI on `0.0.0.0:8080` by default.
- `tests/integration/test_web.py`: HTTP tests for home, create, edit, preview, approve, reject, invalid JSON, Ollama generation, empty source and provider errors.
- `tests/integration/test_api.py`: agent API create/read/update/list, duplicate/closed/applied guards, error codes and absence of approve endpoint.
- Web generation uses an injectable provider factory for tests; production uses `OllamaProvider` with form/env model and URL.
- Documentation audit added in `docs/dev/AUDIT.md`.
- `tests/e2e/web.mjs`: Playwright browser flow against the real server: home, generate form, create, edit pending, approve without commit, reject.
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
- Container verification through the host socket: image built; Compose started on port 18080; container ran as UID 100/GID 101; auto-init created `/data`, 15 schemas and Git with an initial schema commit; healthcheck reached `healthy`; HTTP worked inside the container; a synthetic proposal passed `new`/`list`/`dry-run`/`approve` with a scoped commit; data survived `restart` and `compose down`/`up`; a host bind mount initialized, served HTTP and persisted. Test resources were cleaned up.
- User docs corrected: the image user is UID/GID 100:101, not 1000; the container section now records commands actually run.

## Active

- Container runtime verification is complete. The next work unit is the legacy-surface audit and documentation cleanup.
- No application code changes are pending; only documentation updates are uncommitted.

## Next Steps

1. Audit `ingest`, `export`, `search`, `rebuild`, `timeline`, `genogram` and `conflicts` against `PRD.md` and actual behavior; fix, implement, or mark experimental with matching tests and docs.
2. Decide whether agents need withdraw/reject or generation API endpoints, keeping approval UI/CLI-only.
3. Re-run Python/lint/format/mypy and Playwright checks after any change; keep bilingual docs in sync.
4. Run the optional Ollama container profile only when network/time permit; it remains unverified.

## Checks

- `PYTHONPATH=/data/src python -m pytest -q`: `51 passed`.
- `npm run test:e2e`: Playwright edit, approve and reject flows passed.
- `ruff check src tests`: passed.
- `ruff format --check src tests`: passed.
- `mypy src`: passed.
- `python -m pip wheel --no-deps .`: passed; installed wheel initializes an archive with 15 schemas.
- `sh -n docker-entrypoint.sh`: passed.
- Entrypoint smoke test outside Docker: fresh archive, Git init, initial schema commit, idempotent second run.
- `docker build -t storygram:local /data`: passed against the host daemon.
- `docker compose -p storygram-test up -d` on port 18080: container healthy; non-root `id -u` returned `100`.
- In-container `init-ok`, clean `git status`, initial schema commit and `http-ok`: passed.
- In-container proposal `new` / `list` / `approve --dry-run` / `approve`: passed; commit `feat(proposal): apply proposal:docker-check` created.
- Restart and `compose down`/`up` persistence: canonical record, archived proposal and Git history survived.
- Host bind-mount check: `bind-init-ok`, `bind-http-ok`, `bind-persisted`; cleanup completed.
- Optional Ollama profile: not run.

## Known Limitations

- The adapter CLI requires a running Ollama server; the test suite uses a callable mock and never needs network. The container `llm` profile was not exercised.
- The verified daemon is Podman Engine 5.8.2 exposed through its Docker-compatible API, not a native Docker Engine. Record this distinction in future runs.
- Host-published ports may not be reachable from the development container; validate through container exec/health and treat host UI access separately.
- Bind mounts resolve on the host daemon, not inside the development container. The helper's `/hosttmp/...` path is not the host path; derive or use a fixed host `/tmp` path as documented in `HANDOFF.md`.
- `apply_proposal` commit message is `feat(proposal): apply <id>`.
- The archived proposal records `applied_at`, but not the resulting commit hash, to keep the archive and data commit atomic.
- Conflict detection is deliberately conservative and year-based; it is not a complete temporal reasoner.
- Working-tree cleanliness checks tracked files only, so ignored pending proposals do not block approval.
- Pending proposals remain local and ignored by Git; only merged proposals are archived and committed.
- `export` and `ingest` still need the planned cleanup; `ingest` still only copies files.
- Browser testing on Alpine uses Node Playwright with system Chromium; Python Playwright wheels are not musllinux-compatible.
- The web UI and JSON API have no authentication and bind to `0.0.0.0`; use only in the controlled container/host mapping.
- The API cannot approve; approval remains UI/CLI only.
