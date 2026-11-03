# Current State

Last updated: 2026-11-03

## Git

- Branch: `feature/agent-proposal-flow`
- Recent commits: prompt hardening, export round-trips (`ccb15ef`, `db9f54e`), JSON parser and safe import (`5524000`, `7dcc20d`, `90263a3`), then checksummed capture metadata (`9e143df`); see `git log --oneline -20`.
- Web generation, container files, bilingual docs, pending editing and the JSON API are implemented.
- Proposal engine, CLI, local web UI, Playwright e2e tests, LLM adapter and container files are present.
- The JSON API now supports generate, reject and withdraw; there is still no approve endpoint.
- An OpenAI-compatible provider with bearer-token support was added alongside the Ollama provider.
- The 2026-11-01 API/provider/withdraw work, the legacy command hardening, the 2026-11-02 model-quality fixes and the 2026-11-03 export/import/capture units are committed in small atomic units.
- Python, lint, format, mypy and browser checks pass. The container image was rebuilt and exercised end-to-end with the live LLM endpoint through the host Docker socket, then removed.

## Environment

- Development container was regenerated on 2026-11-01. Alpine 3.24.2, running as root, repository at `/data` bind-mounted from the host.
- Reinstalled after regeneration: `apk add --no-cache python3 py3-pip git nodejs npm chromium docker-cli docker-cli-compose jq`, then `pip install --break-system-packages -e '.[dev]'`.
- Python 3.14.10, Git 2.54.0, pip 26.1.2, Node 24.22.1/npm 11.12.1 and system Chromium.
- Tests use paths relative to `/data` and must be run from the repository root.
- `/var/run/docker.sock` is the host socket. In this session it exposed Podman Engine 5.8.2 through its Docker-compatible API; Docker CLI was 29.9.2 and Compose v5.6.1. This is not Docker-in-Docker; never start `dockerd`.
- Live LLM endpoint for verification: `http://100.64.0.8:8080/v1/chat/completions`, model `qwen3-4b` (llama-swap). The bearer key was supplied by the user, used only through an ephemeral env file, and is not stored in the repository. Keep one model loaded: switching models adds load latency and was explicitly avoided after the 4B reference was chosen.
- Host cgroup: about 3.78 GiB RAM and a 1-core CPU quota (`cpu.max 100000 100000`). This makes the local 3B GGUF impractical even though it fits in memory.

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
- 2026-11-03 export round-trip unit: `export_yaml`, `export_markdown`, `records_from_yaml`, `records_from_jsonld` and `records_from_markdown` added in `export.py`; `export --format` now accepts `yaml` and `markdown`; existing `json`/`jsonld` output is unchanged except the added parsers. `tests/integration/test_export_roundtrip.py` covers Person, Episode and Assertion round-trips, malformed parser input and CLI output parsing.
- 2026-11-03 safe import unit: `src/storygram/importer.py` reads JSON/JSON-LD/YAML/Markdown exports, validates every record schema, builds a create-only proposal and runs `plan_apply` before writing. `storygram import FILE` writes only `proposals/`; canonical `data/` is untouched until human approval. Imported Episode/Source/Annotation records are wired as evidence for later operations; `--evidence` supplies canonical capture IDs. `records_from_json` was added to complete the parser set. `tests/integration/test_import.py` covers all formats, pending-only writes, evidence wiring, duplicate/existing IDs, missing evidence, invalid schemas and explicit format override. Full suite is now `116 passed`.
- 2026-11-03 capture metadata unit: `src/storygram/capture.py` streams the capture into `inbox/` while computing SHA-256 and writes `inbox/.storygram/<filename>.json` with format `storygram.capture/1`, size, MIME type, checksum, `ingested_at` and `overwritten`. Capture and sidecar are written through same-directory temp files and `os.replace`; `--json` exposes the metadata. `tests/integration/test_ingest.py` covers checksums, binary content, JSON output, overwrite refresh and refused-overwrite preservation. Full suite is now `121 passed`.

## Active

- Model-quality unit: `qwen3-4b` is the single reference model. The prompt now produces dry-run-valid proposals for Italian, English and short captures. The local 1.5B model remains a smoke test; the local 3B model was stopped after it produced no tokens in more than 25 minutes on 1 CPU.
- Export round-trip unit is implemented and documented: JSON/JSON-LD/YAML/Markdown exports plus reversible module parsers.
- Safe import and capture metadata are implemented: an export becomes a validated create-only pending proposal, and `ingest` writes a checksummed inbox sidecar. The next product work units are higher-level timelines and endpoint-aware Relationship records.

## Next Steps

1. Extend timelines to place/collection/archive level and model Relationship endpoints before promoting `genogram` beyond experimental.
2. Keep approval UI/CLI-only; consider advisory (non-applying) model review later.
3. Re-run Python/lint/format/mypy and Playwright checks after any change; keep bilingual docs in sync.
4. Keep `qwen3-4b` as the quality reference and do not switch models on the server during a review session. Always dry-run generated proposals before approval.
5. Run the optional Ollama container profile only when network/time permit; it remains unverified.

## Local GGUF Helpers (2026-11-02)

- Added `scripts/download-model.sh` and `scripts/llm-up.sh`, both tracked and executable.
- `download-model.sh` downloads `qwen2.5-1.5b-instruct-q4_k_m.gguf` into `${STORYGRAM_MODELS_DIR:-${STORYGRAM_MODEL_DIR:-<repo>/models}}` and verifies SHA256 `6a1a2eb6d15622bf3c96857206351ba97e1af16c30d7a74ee38970e434e9407e`.
- `llm-up.sh` derives the host-side model path from the development container's `/data` mount when `STORYGRAM_MODELS_DIR` is omitted, then starts the `llm` Compose profile with `STORYGRAM_LLM_PROVIDER=openai`, `STORYGRAM_LLM_URL=http://llm:8080` and the GGUF filename without extension as the model name.
- `compose.yaml` now has an `llm` llama.cpp service using `samueltallet/alpine-llama-cpp-server:latest`, a read-only bind mount, and `LLAMA_ARG_MODEL`/`LLAMA_ARG_HOST`/`LLAMA_ARG_PORT`/`LLAMA_ARG_JINJA`; the Ollama service moved to the `ollama` profile so the names do not collide.
- The helper scripts were syntax-checked, and `docker compose config` passed for the default and `llm` profiles. A stubbed `docker` verified the derived host path and exported provider variables without starting containers.

## Local Model Quality (2026-11-02)

- Reference model: `qwen3-4b` on the configured OpenAI-compatible endpoint. Keep it loaded; do not switch to 8B/14B during normal review.
- Prompt hardening added: Episode `content.text`, evidence on operations, no Relationship records, `relation:*` predicates, `transaction_time.recorded_at` as record time, `valid_time` for source dates, no Period records, only IDs created in the proposal or known, literal facts in `value` without an invented object prefix, and no invented surnames.
- Fixtures: Italian (Maria/Luca/Torino), English (Elena/Naples/Milan/nurse), short capture (garden photo).
- `qwen3-4b` dry-run: Italian passed with 6 operations; English passed after the literal-value example; short capture returned only Episode and passed.
- `qwen3-8b` was not selected: the English fixture failed envelope validation with a `record_type` of `Occupation`.
- Local 1.5B with the hardened prompt: returned only Episode with `content.text` in about 76 seconds; dry-run passed.
- Local 3B: load about 9 minutes / 1.86 GiB; no token in 25+ minutes under the 1-CPU quota; stopped and test resources removed.
- Semantic quality is still limited: `qwen3-4b` produced `place:neapes` (typo) and previously invented a surname. Dry-run validity is not truth; human approval remains mandatory.

## Export Round-Trips (2026-11-03)

- `storygram export --format yaml` emits a YAML sequence of canonical records; `records_from_yaml` parses a sequence, a single mapping or `{records: [...]}`.
- `storygram export --format markdown` emits blocks marked `<!-- storygram:record -->`, each with YAML front matter plus a body. Episode `content.text` and record `notes` move to the body; `storygram_body` records which field is in the body.
- `records_from_jsonld` reverses the existing `@context`/`@graph` output by mapping `@id`/`@type` back to `id`/`type`. JSON-LD remains a local graph projection, not full RDF expansion.
- Round-trip tests cover a Person (smallest case), an Episode with content text, an Assertion with nested valid/transaction time, multiple records, malformed parser input and CLI YAML/Markdown output.
- Lossiness: Markdown body-only edits are ignored because the front matter is the source of truth; JSON/JSON-LD/YAML preserve record data. There is no CLI canonical import, so exported records still cannot bypass the proposal/approval gate.
- Existing `export --format json` and `jsonld` structures are unchanged; the JSON export test remains green.

## Safe Import (2026-11-03)

- `storygram import FILE` accepts exported JSON, JSON-LD, YAML or Markdown; the format is inferred from the suffix or forced with `--format`.
- It parses the export through the round-trip parsers, validates every record against its schema, rejects unknown/non-proposable types, duplicate IDs and IDs already canonical, then builds a create-only proposal with `status=proposed`.
- The proposal is run through `plan_apply` (the same dry-run planner used by approval) before anything is written. Invalid proposals, including missing evidence, fail the import and leave no pending file.
- Imported Episode/Source/Annotation records are ordered first and become operation-level evidence for later records; `--evidence` adds already-canonical capture IDs. Proposal-level evidence is not used because it would be evaluated before newly created records exist.
- `import` writes only `proposals/`. It never writes `data/`, never approves and never creates a Git commit. Canonical records appear only after the normal human `proposal approve` path.
- `--id` defaults to `proposal:import-<file-stem>`; `--title` overrides the generated title.
- `records_from_json` was added as the missing symmetric parser for the native JSON export list; it also accepts a single record or `{records: [...]}`.
- Tests cover JSON/JSON-LD/YAML/Markdown import, auto format detection, `--format` override for unknown suffixes, pending-only writes, approval after import, imported-Episode evidence wiring, missing evidence, invalid schema, duplicate IDs and IDs already in canonical data.

## Capture Metadata (2026-11-03)

- `src/storygram/capture.py` computes SHA-256 while streaming the source into a temp file, so the metadata describes the exact copied bytes without a second read.
- Sidecar path: `inbox/.storygram/<filename>.json`; format identifier `storygram.capture/1`.
- Fields: `filename`, `size`, `mime_type`, `checksum {algorithm: sha256, value}`, `ingested_at`, `overwritten`.
- The capture and sidecar are moved into place with `os.replace`; if the metadata replace fails after the capture replace, the new capture and stale sidecar are removed and the command fails.
- A refused overwrite (`--overwrite` absent) leaves both the original capture and its sidecar untouched. An accepted overwrite refreshes the checksum and sets `overwritten: true`.
- `ingest episode --json` returns the metadata plus the capture and sidecar paths.
- `inbox/` remains the only destination: no canonical `data/` record, proposal or commit is created.
- MIME type is a best-effort guess from the filename and can be `null`.

## Checks

- `PYTHONPATH=/data/src python -m pytest`: `121 passed`.
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
- Capture smoke test: `init` + `ingest episode --json` wrote `inbox/sample.txt` and `inbox/.storygram/sample.txt.json`, checksum matched the content, and `data/` contained 0 files.
- Test container, network, volume, image, temp archives and ephemeral env file were removed.
- `sh -n scripts/download-model.sh scripts/llm-up.sh`: passed.
- `docker compose config` and `docker compose --profile llm config`: passed.
- `scripts/llm-up.sh` with a stubbed `docker`: derived `/mnt/c/Users/erobi/Desktop/storygram_test/models`, set `openai` / `http://llm:8080` / `qwen2.5-1.5b-instruct-q4_k_m`, and passed `--profile llm up -d`.
- Local `llm` profile with `models/qwen2.5-1.5b-instruct-q4_k_m.gguf`: model loaded in about 2m36s, `/health` returned `{"status":"ok"}`, `/v1/models` listed the GGUF, and the read-only mount worked.
- App container on port 18080 with the local profile: reached `healthy`; in-container `proposal generate` returned a valid proposal envelope.
- The 1.5B model with the hardened prompt returned only a minimal Episode with `content.text`; it passes dry-run but does not extract people, places or assertions. This is a model-quality limit, not a wiring failure.
- With the hardened prompt, `qwen3-4b` produced six operations (Episode, two People, Place, two Assertions) for the Italian fixture and passed dry-run. The English fixture also passed after adding a literal-value example; `place:neapes` remained a model typo, so human review is still required.
- `qwen3-14b` and `qwen3-8b` were tested during prompt tuning but are not the chosen reference; avoid switching models on the shared server.
- Optional Ollama profile: not run.
- Remote prompt A/B: `qwen3-4b` passed dry-run on Italian, English and short-capture fixtures; `qwen3-8b` failed envelope validation on the English fixture and was not selected.
- Local 3B GGUF: model loaded (about 9 minutes, 1.86 GiB), then produced no token for more than 25 minutes under the 1-CPU quota; stopped and removed. It was not promoted to default.
- Test containers, project network, the project volume created by this run, and the temporary Alpine image were removed; `storygram:local` and the downloaded GGUF remain.

## Known Limitations

- The default provider is Ollama, but live verification used the OpenAI-compatible `qwen3-4b` endpoint and later the local `llm` llama.cpp profile. The Ollama profile (`--profile ollama`) was not exercised.
- LLM generation validates the proposal envelope only; operation records can still fail the dry-run. The hardened prompt makes `qwen3-4b` outputs dry-run valid on the tested fixtures, but this is not a guarantee for every capture. The local 1.5B model usually returns only an Episode.
- `qwen3-4b` can still invent a surname or misspell a place name (for example `place:neapes`); dry-run validity is not semantic correctness. Human review remains mandatory.
- The local 3B model is not usable on the current 1-CPU quota. It loaded but produced no tokens in 25+ minutes; do not set it as the default.
- There is intentionally no automate-approval or approve endpoint. A model may suggest or classify, but only a human UI/CLI action can apply canonical data.
- `STORYGRAM_LLM_API_KEY` is read from the environment; never place it in Git. `.env` is gitignored and excluded from the Docker build context.
- The verified daemon is Podman Engine 5.8.2 exposed through its Docker-compatible API, not a native Docker Engine. Record this distinction in future runs.
- `scripts/llm-up.sh` assumes the development repository is mounted at `/data` when deriving the host model path; otherwise set `STORYGRAM_MODELS_DIR` explicitly.
- The local GGUF must exist on the host daemon's side of the bind mount. A development-container path is not a host path.
- The local Qwen 1.5B model loads in about 2m36s and may trigger transient app healthcheck failures under CPU contention; wait for both services before testing generation. Generation of a minimal Episode took about 76 seconds in the last run.
- Do not switch models on the llama-swap server during a session; loading a different model adds latency and the user asked to keep the 4B reference stable.
- Host-published ports may not be reachable from the development container; validate through container exec/health and treat host UI access separately.
- Bind mounts resolve on the host daemon, not inside the development container. The helper's `/hosttmp/...` path is not the host path; derive or use a fixed host `/tmp` path as documented in `HANDOFF.md`.
- `apply_proposal` commit message is `feat(proposal): apply <id>`.
- The archived proposal records `applied_at`, but not the resulting commit hash, to keep the archive and data commit atomic.
- Conflict detection is deliberately conservative and year-based; it is not a complete temporal reasoner.
- Working-tree cleanliness checks tracked files only, so ignored pending proposals do not block approval.
- Pending proposals remain local and ignored by Git; only merged proposals are archived and committed.
- `ingest` writes a local `storygram.capture/1` sidecar with SHA-256, size, MIME type and timestamps under `inbox/.storygram/`. The sidecar is not a canonical Episode and is not validated by the record registry.
- Capture MIME type is best-effort via Python `mimetypes`; unknown types are recorded as `null`.
- `export` supports JSON, YAML, Markdown and a minimal JSON-LD projection. JSON/YAML/JSON-LD round-trip through module parsers; Markdown round-trips only through front matter.
- `import` turns an export into a create-only pending proposal; it never writes canonical data. Records whose type requires evidence need either an imported Episode/Source/Annotation or `--evidence`; otherwise the import fails at validation.
- `genogram` remains experimental until `Relationship` models endpoints and relation type.
- `timeline` covers entity/place matches only; collection/archive-level timelines remain open.
- Browser testing on Alpine uses Node Playwright with system Chromium; Python Playwright wheels are not musllinux-compatible.
- The web UI and JSON API have no authentication and bind to `0.0.0.0`; use only in the controlled container/host mapping.
- The API cannot approve; approval remains UI/CLI only.
