# Current State

Last updated: 2026-11-01

## Git

- Branch: `feature/agent-proposal-flow`
- Recent commits: API/provider/withdraw series followed by the legacy command hardening series; see `git log --oneline -20`.
- Web generation, container files, bilingual docs, pending editing and the JSON API are implemented.
- Proposal engine, CLI, local web UI, Playwright e2e tests, LLM adapter and container files are present.
- The JSON API now supports generate, reject and withdraw; there is still no approve endpoint.
- An OpenAI-compatible provider with bearer-token support was added alongside the Ollama provider.
- The 2026-11-01 API/provider/withdraw work and the legacy command hardening are committed in small atomic units. No tracked changes are pending in this unit.
- Python, lint, format, mypy and browser checks pass. The container image was rebuilt and exercised end-to-end with the live LLM endpoint through the host Docker socket, then removed.

## Environment

- Development container was regenerated on 2026-11-01. Alpine 3.24.2, running as root, repository at `/data` bind-mounted from the host.
- Reinstalled after regeneration: `apk add --no-cache python3 py3-pip git nodejs npm chromium docker-cli docker-cli-compose jq`, then `pip install --break-system-packages -e '.[dev]'`.
- Python 3.14.10, Git 2.54.0, pip 26.1.2, Node 24.22.1/npm 11.12.1 and system Chromium.
- Tests use paths relative to `/data` and must be run from the repository root.
- `/var/run/docker.sock` is the host socket. In this session it exposed Podman Engine 5.8.2 through its Docker-compatible API; Docker CLI was 29.9.2 and Compose v5.6.1. This is not Docker-in-Docker; never start `dockerd`.
- Live LLM endpoint for verification: `http://100.64.0.8:8080/v1/chat/completions`, model `qwen3-4b` (llama-swap). The bearer key was supplied by the user, used only through an ephemeral env file, and is not stored in the repository.

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
  - `proposal new|list|show|approve|reject|withdraw|generate` implemented.
  - `approve` supports `--dry-run`, `--no-commit` and scoped Git commits.
- `tests/integration/test_cli_proposals.py`: CLI coverage for init, proposal lifecycle, dry-run, no-commit, commit, reject and invalid input.
- `src/storygram/web.py`: stdlib HTTP UI with home, proposal list, JSON create form, Ollama Generate page, pending edit page, dry-run preview, approve (commit/no-commit) and reject.
- JSON API: `GET/POST /api/proposals`, `GET/PUT /api/proposals/<id>`, `POST /api/proposals/generate`, `POST /api/proposals/<id>/reject`, `POST /api/proposals/<id>/withdraw`; no approve endpoint.
- `src/storygram/cli.py`: `web` command serving the UI on `0.0.0.0:8080` by default.
- `tests/integration/test_web.py`: HTTP tests for home, create, edit, preview, approve, reject, withdraw, invalid JSON, generation, empty source and provider errors.
- `tests/integration/test_api.py`: agent API create/read/update/list/generate/reject/withdraw, duplicate/closed/applied guards, error codes and absence of approve endpoint.
- Web generation uses an injectable provider factory for tests; production resolves Ollama or an OpenAI-compatible provider from form/env values.
- Documentation audit added in `docs/dev/AUDIT.md`.
- `tests/e2e/web.mjs`: Playwright browser flow against the real server: home, generate form, create, edit pending, approve without commit, reject.
- `package.json` / `package-lock.json`: Playwright Node dependency and `npm run test:e2e`.
- `.gitignore`: `node_modules/` ignored.
- `src/storygram/llm.py`: provider-agnostic adapter, callable mock provider, stdlib Ollama provider, prompt builder, JSON extraction, normalization, pending-only save.
- Adapter always forces `type=Proposal`, `status=proposed` and fresh timestamps; unknown model fields are dropped.
- `proposal generate`: CLI command; supports `--file`, `--text`, `--provider`, `--model`, `--url`, deprecated `--ollama-url`, `--api-key`, `--no-save`, `--json` and the `$STORYGRAM_LLM_*` variables.
- `tests/integration/test_llm_adapter.py`: generation, fenced/thinking JSON, unknown-field removal, pending-only writes, duplicate rejection, invalid/empty input, Ollama and OpenAI request/auth shapes, env config and error redaction.
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
- 2026-11-01 API work: `POST /api/proposals/generate`, `POST /api/proposals/<id>/reject` and `POST /api/proposals/<id>/withdraw`; no approve endpoint.
- `withdrawn` is now a proposal status (schema root duplicate kept identical, `models.py` and engine guards updated).
- `withdraw_proposal` and a shared close helper distinguish missing (404), already closed (409) and success.
- CLI `proposal withdraw`; web detail page exposes Withdraw; web Generate form accepts provider, model and URL.
- `OpenAICompatibleProvider` calls `/v1/chat/completions`, supports `Authorization: Bearer`, hides the key from its repr and error text, and is aliased as `LlamaCppProvider`.
- Provider resolution: `$STORYGRAM_LLM_PROVIDER`, `$STORYGRAM_LLM_MODEL`, `$STORYGRAM_LLM_URL`, `$STORYGRAM_LLM_API_KEY`; Ollama still honors `$STORYGRAM_OLLAMA_*`. Default provider remains `ollama`.
- Prompt now includes lowercase ID rules, `record_type` requirements, a minimal valid proposal shape, and strips `<thinking>` blocks before JSON extraction.
- Compose passes the `STORYGRAM_LLM_*` variables into the app container; `.env` stays gitignored and excluded from the build context.
- Tests: API generate/save/no-save/error, reject/withdraw, provider request/auth/error, thinking-block extraction, CLI withdraw, web withdraw.
- Live verification: real qwen3-4b generation returned 201 and a pending proposal; withdraw returned 200 and a second withdraw 409.
- Container re-verification: image rebuilt, app started on port 18080 with the live LLM env, reached healthy, reached the LLM endpoint, generated a pending proposal, withdrew it through the API, survived restart and `down`/`up`, then all test resources and the image were removed.
- `ingest` now uses the PRD grammar `ingest episode FILE`, copies only into `inbox/`, adds `--archive`, refuses silent overwrites and cannot write canonical data.
- `export` uses the registry, sorts by ID, fails on malformed JSON, adds `--archive`, excludes records without visibility when filtering, and emits a minimal JSON-LD `@id`/`@type` graph.
- `rebuild` and `search` now use an idempotent SQLite/FTS5 index with a signature check, exact ID/type matching, content fallback, deterministic ordering and reports for malformed records.
- `conflicts` merges explicit and assertion-derived contradictions, applies status filters to both, deduplicates unordered pairs and includes both assertion records plus evidence.
- `timeline` excludes superseded/archived/rejected assertions, sorts by valid-time start, includes evidence fields and distinguishes unknown records from known records with no entries.
- `genogram` is explicitly experimental, scopes relations to `relation:*` assertions for the requested person, marks unsupported predicates and ignores unscoped Relationship records.
- `get` and `list` now accept `--archive`, matching the documented examples.
- New tests: `test_ingest.py` CLI coverage, `test_export.py`, `test_search.py`, `test_conflicts.py`, `test_timeline.py`, `test_genogram.py`, `test_read_cli.py`.

## Active

- API generate/reject/withdraw, the OpenAI-compatible provider and the legacy command hardening are implemented, tested and committed.
- The next work unit is the remaining product gaps: real JSON-LD/YAML/Markdown round-trips, capture metadata, higher-level timelines and endpoint-aware Relationship records.

## Next Steps

1. Implement real JSON-LD and YAML/Markdown round-trip export, or explicitly keep JSON-only in `PRD.md`/docs.
2. Add capture metadata/checksums to `ingest` without allowing canonical writes.
3. Extend timelines to place/collection/archive level and model Relationship endpoints before promoting `genogram` beyond experimental.
4. Keep approval UI/CLI-only; consider advisory (non-applying) model review later.
5. Re-run Python/lint/format/mypy and Playwright checks after any change; keep bilingual docs in sync.
6. Run the optional Ollama container profile only when network/time permit; it remains unverified.

## Checks

- `PYTHONPATH=/data/src python -m pytest -q`: `86 passed`.
- `npm run test:e2e`: Playwright edit, approve and reject flows passed.
- `ruff check src tests`: passed.
- `ruff format --check src tests`: passed.
- `mypy src`: passed.
- Live CLI generation against `qwen3-4b`: returned `ok: true` and a pending proposal.
- Live API generation: `201`, saved pending; `withdraw`: `200`; repeated `withdraw`: `409`.
- `docker build -t storygram:local /data`: passed after the compose/provider changes.
- Compose run on port 18080 with the live LLM env: `healthy`, UID `100`, `init-ok`, `http-ok`.
- In-container LLM reachability: `/v1/models` returned 4 models.
- In-container generation: `ok: true`; generated pending proposal saved.
- In-container API withdraw: `200`; repeated withdraw: `409`.
- Restart and `down`/`up` persistence: pending proposal survived.
- Legacy CLI tests: ingest, export, search/rebuild, conflicts, timeline, genogram and read commands all pass.
- Test container, network, volume, image, temp archives and ephemeral env file were removed.
- Optional Ollama profile: not run.

## Known Limitations

- The default provider is Ollama, but the live verification used the OpenAI-compatible `qwen3-4b` endpoint. The container `llm` Ollama profile was not exercised.
- LLM generation validates the proposal envelope only; operation records can still fail the dry-run. The live qwen3-4b output did exactly that, so generation is not a guarantee of an applicable proposal.
- There is intentionally no automate-approval or approve endpoint. A model may suggest or classify, but only a human UI/CLI action can apply canonical data.
- `STORYGRAM_LLM_API_KEY` is read from the environment; never place it in Git. `.env` is gitignored and excluded from the Docker build context.
- The verified daemon is Podman Engine 5.8.2 exposed through its Docker-compatible API, not a native Docker Engine. Record this distinction in future runs.
- Host-published ports may not be reachable from the development container; validate through container exec/health and treat host UI access separately.
- Bind mounts resolve on the host daemon, not inside the development container. The helper's `/hosttmp/...` path is not the host path; derive or use a fixed host `/tmp` path as documented in `HANDOFF.md`.
- `apply_proposal` commit message is `feat(proposal): apply <id>`.
- The archived proposal records `applied_at`, but not the resulting commit hash, to keep the archive and data commit atomic.
- Conflict detection is deliberately conservative and year-based; it is not a complete temporal reasoner.
- Working-tree cleanliness checks tracked files only, so ignored pending proposals do not block approval.
- Pending proposals remain local and ignored by Git; only merged proposals are archived and committed.
- `ingest` is intentionally a safe capture copy into `inbox/`; it does not add checksums or capture metadata yet.
- `export` supports JSON and a minimal JSON-LD projection only; YAML/Markdown round-trips are not implemented.
- `genogram` remains experimental until `Relationship` models endpoints and relation type.
- `timeline` covers entity/place matches only; collection/archive-level timelines remain open.
- Browser testing on Alpine uses Node Playwright with system Chromium; Python Playwright wheels are not musllinux-compatible.
- The web UI and JSON API have no authentication and bind to `0.0.0.0`; use only in the controlled container/host mapping.
- The API cannot approve; approval remains UI/CLI only.
