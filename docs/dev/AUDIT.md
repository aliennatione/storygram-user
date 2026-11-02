# Self-Audit Log

## 2026-10-30 - after proposal CLI, before Playwright

### Final objective

A local-first, deterministic Storygram where humans and external agents can submit explicit proposals, review them in a UI, approve them into canonical history, and keep every applied change in Git. The core must remain usable offline without an LLM. The LLM adapter is optional and may only create reviewable proposals. The final deliverable must be containerizable with an optional local Ollama service in Compose.

### Current objective

Finish the user-facing loop: local web review UI, Playwright end-to-end coverage, then the provider-agnostic LLM adapter. Keep CLI and UI on the same engine so behavior cannot drift.

### Point of the situation

- Proposal schema, registry, full validation, apply engine and CLI proposal lifecycle are implemented.
- The engine rejects bad metadata, missing evidence, unmodelled conflicts, invalid supersession and non-archivable records.
- Approval is atomic with rollback and a scoped Git commit by default.
- A minimal stdlib web UI now exists with proposal list/detail/create/approve/reject and dry-run preview.
- Engine and CLI are covered by tests; web routes have initial HTTP tests.
- `pytest` passes, `ruff check` passes, `ruff format --check` passes and `mypy` passes.
- The repository still contains pre-existing artifacts (`archive/`, `chatgpt.md`, session notes and planning files). They are untracked and not used by the application.
- README/PRD/docs still describe the older MVP and not the new proposal/UI workflow.
- Playwright and the LLM adapter are not implemented.

### Repo review notes

- Application sources are in `src/storygram/`; canonical schemas in `schema/` with root duplicates.
- `data/` is still effectively empty; tests use temporary archives and fixtures.
- `generated/`, `inbox/`, `proposals/` and `media-manifest/` remain local/ignored except `.gitkeep`.
- Existing domain invariants still hold: no auto-confirmation, no overwrites of history, no silent deletion, conflicts explicit.
- The UI is intentionally local and unauthenticated; binding to `0.0.0.0` is only acceptable in this controlled container.

### Calibration

1. Do not expand record semantics before the proposal loop is end-to-end tested.
2. Add Playwright against the real server and a temporary archive, not mocks.
3. After Playwright, build the LLM adapter as a proposal generator with a narrow, mockable interface.
4. Then update bilingual docs and README commands.
5. Finally containerize the application and add an optional local Ollama Compose profile, keeping the offline core usable without it.
6. Keep `STATE.md`, `DECISIONS.md`, `LESSONS.md` and this audit current with each milestone.

## 2026-10-30 - after Playwright and adapter

### Final objective

Ship a local-first, deterministic Storygram with an agent proposal -> human review -> atomic merge loop, optional LLM generation that cannot self-apply, and a containerizable deployment with optional local Ollama.

### Current objective

Close the adapter milestone, then update docs and package the tested surface without making Ollama mandatory.

### Point of the situation

- The browser loop is covered by real Playwright against the real web server on a temporary archive.
- The LLM adapter exists with a mock provider and an Ollama provider; generation returns memory only and persistence is pending-only.
- CLI `proposal generate` is wired to the adapter and supports `--no-save`.
- Tests use no network and assert generated proposals never write canonical records before approval.
- Full suite is green, lint/format/mypy are clean, and browser e2e passes.
- Remaining work is documentation and containerization.

### Calibration

1. Do not let container convenience weaken the human approval gate.
2. Keep the default image offline-capable; Ollama belongs to an optional Compose profile.
3. Re-run Python and browser checks inside the packaged setup.
4. Update README/docs only with commands that were actually executed.

## 2026-10-30 - final package and docs

### Final objective

Deliver a deterministic, local-first Storygram with proposal review, optional LLM generation that cannot self-apply, bilingual docs and a container path with optional local Ollama.

### Current objective

Package the tested surface without pretending Docker runtime was verified inside the Alpine development container.

### Point of the situation

- Proposal engine, CLI, web UI, Playwright flows and LLM adapter are implemented and tested.
- Schema discovery now works for archive-local, repository, package and `$STORYGRAM_SCHEMA_DIR` layouts.
- A wheel builds and initializes a fresh archive with 15 schemas.
- Dockerfile, entrypoint and Compose files exist and pass static checks only; Docker was intentionally not run here.
- Bilingual README/docs now describe the shipped workflow and clearly mark container runtime verification as pending.
- Repository artifacts (`archive/`, session notes, `chatgpt.md`) remain untracked and outside the application.

### Calibration

1. Verify Docker on a capable host before calling the container deliverable verified.
2. Keep the human approval gate and Ollama optionality intact in any packaging change.
3. Do not broaden scope into editing/API work before the current documentation commit is complete.

## 2026-10-30 - pre-export web generation

### Final objective

A local-first Storygram with reviewable agent proposals, optional local LLM generation, atomic human approval and a container path with optional Ollama.

### Current objective

Close the last user-facing gap before export: generate proposals from the web UI without weakening the approval gate.

### Point of situation

- The web UI now has a Generate page backed by the same adapter and pending-save path as the CLI.
- Tests cover generation, empty input and provider failure; E2E covers navigation and form rendering.
- Generated proposals remain pending only; canonical data is unchanged until approval.
- Full Python, lint, format, mypy and browser checks pass.
- Docker runtime remains unverified, as requested in this development container.

### Calibration

1. The web-generation feature is committed; the session is ready for export.
2. Hand off Docker runtime verification and optional editing/API work.
3. Do not claim browser-side Ollama success; only the injected provider path is tested.

## 2026-10-30 - pending editing and agent API

### Final objective

A local-first Storygram where humans and external agents submit reviewable proposals, humans keep final approval, and optional LLM generation still cannot mutate canonical data.

### Current objective

Close the two requested gaps: editing pending proposals and a JSON API for external agents.

### Point of situation

- Pending proposals can be edited in the web UI and via `PUT /api/proposals/<id>`.
- Editing preserves `created_at`, refreshes `updated_at`, forbids ID changes and blocks applied/closed proposals.
- External agents can list, create, read and update pending proposals over JSON.
- No API approval endpoint exists; the human approval gate remains intact.
- UI and API share the same engine helpers and atomic pending writes.
- Python, lint, format, mypy and browser e2e pass.

### Calibration

1. Commit this work before export.
2. Hand off only Docker runtime verification and optional legacy cleanup.
3. Do not expose the unauthenticated API beyond a controlled local network.

## 2026-10-30 - socket-mounted Docker handoff

### Final objective

A deterministic local-first Storygram with a verified container deliverable, human approval gate and optional offline-capable LLM generation.

### Current objective

Prepare a compact, accurate handoff for a next session running in a container with the host Docker socket mounted.

### Point of situation

- Proposal workflow, web UI, JSON API, LLM adapter and bilingual docs are complete and tested: `51 passed`, E2E edit/approve/reject.
- Docker artifacts exist but have never been built or run.
- The next environment uses client-to-host-daemon access, not Docker-in-Docker.
- `AGENTS.md`, `STATE.md`, new `HANDOFF.md`, `PLAN.md`, `RESUME.md`, `DECISIONS.md` and `LESSONS.md` now describe the socket workflow and its path/port pitfalls.
- No application code changed in this documentation pass.

### Calibration

1. Verify Docker before changing product scope.
2. Use a unique project name/port and clean only created resources.
3. Never treat a development-container bind path as a host bind path.
4. Record actual Docker results before calling the container verified.

## 2026-10-31 - container runtime verified

### Final objective

A deterministic local-first Storygram with a verified container deliverable, human approval gate and optional offline-capable LLM generation.

### Current objective

Execute the pending container verification through the host Docker socket and record real results.

### Point of situation

- The development container lacked Git, Python, Docker CLI, Node and Chromium at session start. Installed Docker client/Compose, Git, Python, dev dependencies, Node and Chromium as needed.
- `/var/run/docker.sock` exposed Podman Engine 5.8.2 through its Docker-compatible API. Docker CLI 29.9.2 and Compose v5.6.1 reached it.
- `docker build -t storygram:local /data` succeeded.
- Compose named-volume run on port 18080: UID 100, auto-init, 15 schemas, initial Git commit, `healthy`, `http-ok`.
- In-container proposal lifecycle passed, including dry-run and a scoped `feat(proposal): apply ...` commit.
- Persistence passed across `restart` and across `compose down`/`up` without deleting the volume.
- Host bind mount passed (`bind-init-ok`, `bind-http-ok`, `bind-persisted`).
- Python suite `51 passed`; ruff, format, mypy and Playwright E2E all passed after installing dependencies.
- Test container, volume, network and image were removed. The unrelated `OC-storygram` development container was left running.
- Optional Ollama profile was not run.
- User docs and agent working-memory files were updated with actual commands/results and committed in atomic local commits.

### Calibration

1. Mark M9 complete; move to the legacy-surface audit.
2. Keep the approval gate UI/CLI-only.
3. Document the actual engine (Podman-compatible) rather than implying native Docker Engine.
4. Run the optional Ollama profile only when network/time permit.

## 2026-11-01 - API generation and close endpoints

### Current objective

Expose generation, rejection and withdrawal to agent clients while preserving the human approval gate, and support the user's OpenAI-compatible endpoint.

### Point of situation

- The development container was regenerated as root and required reinstalling Python, pip, Git, Node/npm, Chromium, Docker CLI/Compose and jq.
- The mounted host socket still exposed Podman Engine 5.8.2; Docker CLI 29.9.2 and Compose v5.6.1 reached it.
- The live LLM endpoint was `http://100.64.0.8:8080`, model `qwen3-4b`; bearer authentication was required.
- Added `withdrawn` status, reject/withdraw/generate API routes, CLI withdraw, web withdraw, and an OpenAI-compatible provider with environment configuration.
- Updated tests and bilingual API/contract/README docs.
- Python suite `61 passed`; ruff, format, mypy and Playwright all passed.
- Live CLI and HTTP generation worked; withdraw returned 200 and a repeated withdraw 409.
- Rebuilt the container, ran it with the live LLM env, reached `healthy`, verified non-root UID 100, init, `/v1/models`, generation, API withdraw and persistence across restart and recreation.
- Generated qwen3-4b operation records failed the dry-run, confirming that generation is not a substitute for review.
- Auto-approval was not implemented. The proposal/API path remains unable to apply canonical data.
- Removed the test container, network, volume, image, temporary archives and ephemeral env file.
- The 2026-11-01 changes remain uncommitted because the user did not request a commit.

### Calibration

1. Keep approval UI/CLI-only; reject any request for an agent/API approve path or LLM auto-approval.
2. Treat `withdrawn` and `rejected` as distinct terminal statuses and keep the schema copies identical.
3. Keep provider credentials in the environment; never log, commit or print them.
4. Always dry-run generated proposals; model output can be envelope-valid and record-invalid.
5. Next: legacy-surface audit (`ingest`, `export`, `search`, `rebuild`, `timeline`, `genogram`, `conflicts`).

## 2026-11-01 - legacy command hardening

### Current objective

Close the deterministic legacy-surface gaps without weakening the approval gate, and document only behavior that actually runs.

### Point of situation

- A read-only audit confirmed functional bugs in all seven legacy commands: `ingest --data` bypass, export visibility leak, duplicate FTS rows and stale results, conflict suppression/filtering bugs, superseded timeline entries, global genogram output and a misleading `rebuild` help string.
- No legacy command had an end-to-end CLI test.
- Fixes were committed atomically: ingest, export, index/search/rebuild, conflicts, timeline and genogram, followed by a formatting commit and `get`/`list --archive`.
- `ingest episode` now captures only into `inbox/` and refuses silent overwrites.
- Export is registry-driven, sorted, privacy-safe under filters and fails on malformed JSON; JSON-LD is minimal and explicitly documented as such.
- The search index is rebuilt idempotently, refreshes on file changes and supports exact ID/type plus content search.
- Conflicts merge explicit and derived entries with deduplication, evidence and status filtering.
- Timeline excludes closed assertions, sorts deterministically and includes evidence; genogram is scoped and marked experimental.
- Bilingual README and guide docs now include a "Legacy and derived commands" section with the real options and limitations.
- Tests: `86 passed`; ruff, format, mypy and Playwright E2E passed.

### Calibration

1. Keep ingest capture-only; never add a canonical-write shortcut.
2. Keep export filtering default-deny and document JSON-LD/YAML/Markdown limits honestly.
3. Keep the search index deterministic and rebuildable; report malformed input instead of skipping silently.
4. Keep genogram experimental until Relationship models endpoints and relation type.
5. Next: higher-level timelines, real JSON-LD/YAML/Markdown round-trips and capture metadata.

## 2026-11-02 - local GGUF helpers and llama.cpp profile

### Current objective

Track the previously untracked model helpers and make them consistent with the Compose runtime, without changing the approval gate.

### Point of situation

- `scripts/download-model.sh` and `scripts/llm-up.sh` were untracked; `llm-up.sh` had no corresponding Compose service and used a different model-directory variable than the downloader.
- Added an `llm` llama.cpp service, read-only model bind, `LLAMA_ARG_*` configuration, and moved Ollama to the `ollama` profile.
- Normalized `STORYGRAM_MODELS_DIR` (plural) with a fallback to the older singular name.
- `llm-up.sh` now derives the host model path from the development container's `/data` mount and exports the provider, URL and model name before starting Compose.
- Both scripts are tracked with mode `755`, syntax-checked and covered by a stubbed-`docker` wiring check.
- Real run with `models/qwen2.5-1.5b-instruct-q4_k_m.gguf`: model loaded in about 2m36s, health and model listing passed, read-only mount worked, app reached `healthy`, and in-container generation returned a valid proposal envelope.
- The small model produced a minimal Episode with no content/evidence; it is schema-valid and passes dry-run, confirming that generation is not applicability or quality.
- Removed the test containers, network, project volume and temporary Alpine image. Kept the downloaded model and `storygram:local`.
- Python suite `86 passed`; ruff, format and mypy passed.

### Calibration

1. Keep the model file untracked and mounted read-only.
2. Keep `llm` for llama.cpp and `ollama` for Ollama; do not reuse profile names.
3. Keep the tiny model as a transport smoke test, not a quality baseline.
4. Always dry-run generated records; transport success is not schema success.
5. Next: choose a larger local GGUF for quality, or leave local inference as an optional smoke path.

## 2026-11-02 - model quality and prompt hardening

### Current objective

Determine whether a larger local GGUF should replace the 1.5B smoke-test model, and harden the proposal prompt so `qwen3-4b` produces dry-run-valid operations. Keep the human approval gate unchanged.

### Point of situation

- The local 1.5B model produced only a minimal Episode. The local 3B model was downloaded and loaded, but produced no token for more than 25 minutes under the 1-CPU quota; it was stopped and removed.
- The prompt previously allowed invalid operations: missing `transaction_time` on Assertion, Period records with unsupported `start_year`/`end_year`, Relationship records without endpoints, and invented entity prefixes such as `occupation:nurse`.
- A `_new_record_path` crash on an invalid generated `record_type` was fixed with a regression test.
- Prompt hardening added required fields, `relation:*` predicates, literal `value` examples, evidence rules, ID-reference rules and explicit avoidance of Relationship/Period records.
- `qwen3-4b` produced six dry-run-valid operations for the Italian fixture and a valid short-capture Episode. The English fixture passed after adding the literal-value example.
- `qwen3-8b` failed envelope validation on the English fixture (`record_type: Occupation`) and was not selected. `qwen3-14b` was only used during prompt tuning; it is not the reference.
- `place:neapes` remained a model typo, confirming that dry-run validity is not semantic correctness.
- The local 1.5B model, with the hardened prompt, returned only an Episode with `content.text` in about 76 seconds; it passed dry-run but did not extract people, places or assertions.

### Calibration

1. Keep `qwen3-4b` as the single quality reference; do not switch models on the shared server during normal review.
2. Keep the 1.5B model as a smoke test and do not promote the 3B model on 1 CPU.
3. Keep the prompt's field-level examples; prohibitions alone are not reliable for small models.
4. Keep generation separate from approval. Always dry-run and review; dry-run validity is not truth.
5. Next: run the same prompt against a second real capture if needed, then return to the remaining product gaps.
