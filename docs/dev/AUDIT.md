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

## 2026-11-03 - export round-trips

### Current objective

Close the JSON-LD/YAML/Markdown export round-trip gap without changing the existing JSON export or the human approval gate.

### Point of situation

- `export_json` and `export_jsonld` output shapes were preserved; `--format` now also accepts `yaml` and `markdown`.
- Added reversible module parsers: `records_from_yaml`, `records_from_jsonld` and `records_from_markdown`.
- YAML is a lossless record sequence. JSON-LD reverses the existing `@id`/`@type` graph projection. Markdown uses YAML front matter plus a body for Episode `content.text` or `notes`, with `storygram_body` as the reconstruction marker.
- Round-trip tests start from the smallest single Person case and extend to an Episode, a nested Assertion, multiple records, malformed input and CLI output.
- The full suite is `103 passed`; ruff, format, mypy and Playwright E2E pass.
- No canonical import CLI was added, so exported records still cannot bypass proposals, validation or human approval.
- Lossiness is documented: Markdown body-only edits are ignored; JSON-LD is a local projection, not full RDF.

### Calibration

1. Keep JSON/JSON-LD output stable; add formats without changing existing contracts.
2. Keep the front matter as the Markdown source of truth unless a reviewed editing model is introduced.
3. Any future import path must create pending proposals or inbox captures, never canonical writes.
4. Next product gaps: capture metadata, higher-level timelines and endpoint-aware Relationship records for genograms.

## 2026-11-03 - safe import of exports

### Current objective

Add the smallest safe import step for exported records without bypassing proposals, validation or human approval.

### Point of situation

- Added `records_from_json` and a new `importer.py` that reads JSON, JSON-LD, YAML and Markdown exports.
- Import validates each record schema, rejects non-proposable types, duplicate IDs and IDs already canonical, then runs the approval dry-run planner before writing.
- The result is a create-only pending proposal under `proposals/`; canonical `data/` is untouched until a human approves it.
- Imported evidence records are ordered first and attached as operation-level evidence; `--evidence` covers captures already canonical.
- CLI: `storygram import FILE` with format inference, explicit override, proposal ID/title and JSON output.
- Tests cover all formats, auto-detection, pending-only writes, post-import approval, evidence wiring, missing evidence, invalid schema, duplicate/existing IDs and format override.
- Full suite `116 passed`; ruff, format, mypy and Playwright E2E pass.

### Calibration

1. Keep import proposal-only; never add a canonical write or auto-approval path.
2. Keep the dry-run planner as the import precondition so pending proposals are immediately reviewable.
3. Next product gaps: capture metadata/checksums, higher-level timelines and endpoint-aware Relationship records.

## 2026-11-03 - capture metadata and checksums

### Current objective

Add capture metadata/checksums to `ingest` while keeping `inbox/` as the only destination and preserving the human approval gate.

### Point of situation

- Added `src/storygram/capture.py`: streams the capture to a temp file while computing SHA-256, preserves source stat metadata, then moves the capture into `inbox/`.
- Writes a versioned sidecar at `inbox/.storygram/<filename>.json` with filename, size, best-effort MIME type, SHA-256, `ingested_at` and `overwritten`.
- Capture and sidecar use same-directory temp files and `os.replace`; a failed sidecar move removes the newly replaced capture and stale sidecar.
- `ingest episode` now supports `--json`; plain output reports size, checksum and the sidecar path.
- Refused overwrites keep both the original capture and metadata; accepted overwrites refresh both.
- Inbox or metadata-directory preparation failures are wrapped in `CaptureError` with the source path.
- No canonical record, proposal or Git commit is created by ingestion.
- Tests cover checksum/size/MIME, binary content, JSON output, overwrite refresh and refused-overwrite preservation.
- Full suite `121 passed`; ruff, format, mypy and Playwright E2E pass.

### Calibration

1. Keep capture metadata in `inbox/`; never write it under `data/`.
2. Do not treat a sidecar as a canonical Episode or as evidence until a reviewed proposal says so.
3. Next product gaps: higher-level timelines and endpoint-aware Relationship records.

## 2026-11-04 - endpoint-aware Relationship records

### Current objective

Close the Relationship endpoint gap that blocks a real genogram, without changing the human approval gate or writing canonical data.

### Point of situation

- `Relationship` previously carried only common metadata, so genogram could only use `relation:*` assertions and warned that every Relationship record was ignored.
- The schema now models an optional `subject`/`predicate`/`object` triple. The fields are all-or-nothing: any endpoint field requires all three, while bare legacy records remain valid.
- The root and `schema/` copies of `relationship.schema.json` are byte-identical.
- `models.Relationship` mirrors the optional fields; validation remains schema-driven.
- `genogram` now reads complete Relationship records and `relation:*` assertions, scopes both to the requested person, skips closed relations and warns on incomplete endpoints.
- Output preserves `assertion_id` for assertions and adds `relationship_id`, `record_id` and `record_type`.
- Generation still prefers Assertions; the prompt no longer claims Relationship lacks endpoints.
- Tests cover endpoint validation, complete/incomplete Relationship records, person scoping, closed relations and the CLI warning path.
- Full suite is `124 passed`; ruff, format, mypy and Playwright E2E pass.
- No canonical write path, proposal flow, approval gate or commit behavior changed.

### Calibration

1. Keep Relationship endpoints optional-but-complete so existing archives do not break while new records are fully modelled.
2. Keep genogram experimental until duplicate representations and temporal validity are reviewed against real fixtures.
3. Next product gap: collection/archive-level timelines; place timelines already work through object-side assertion matches.

## 2026-11-04 - collection and archive timelines

### Current objective

Close FR-010 by extending the deterministic timeline from entity/place matches to collection and archive scopes, without changing canonical data or the approval gate.

### Point of situation

- `build_timeline(root, record_id)` already matched assertions on either side of the requested entity, so place timelines worked through object-side matches.
- `build_timeline(root)` now builds an archive-level timeline over every open assertion; `storygram timeline --all` exposes it.
- A collection timeline includes assertions about the collection and assertions about records that assert `relation:member_of` the collection. Membership is a normal Assertion, so no schema change was required.
- Membership expansion is one level deep; nested collections remain open.
- `--all` and a record ID are mutually exclusive and one is required. The empty archive case is handled separately from the unknown-record case.
- Closed assertions remain excluded in all scopes; sorting by valid-time start then assertion ID and evidence fields are unchanged.
- Tests cover archive inclusion, collection members, closed membership, CLI scope validation and the empty-archive message.
- Full suite is `129 passed`; ruff, format, mypy and Playwright E2E pass.
- No canonical write path, proposal flow, approval gate or commit behavior changed.

### Calibration

1. Keep collection membership in Assertions unless a reviewed Collection membership model is introduced.
2. Keep all timeline scopes subject to the same closed-status filter and deterministic ordering.
3. Next product gap: keep `genogram` experimental and review duplicate relationship representations; timelines are complete for the current model.

## 2026-11-04 - genogram deduplication

### Current objective

Remove duplicate genogram entries when the same relation is represented by both an Assertion and a Relationship, without changing canonical data or the approval gate.

### Point of situation

- `genogram` collected complete Relationship records first and then `relation:*` assertions, so the same triple could appear twice.
- Relations are now grouped by exact `(subject, predicate, object)`.
- A Relationship representative is preferred over an Assertion; ties within a type are resolved by sorted `record_id`.
- Each merged entry includes `related_ids`, the sorted IDs of every contributing record, while preserving existing `assertion_id`/`relationship_id`/`record_id`/`record_type` keys.
- Distinct predicates for the same endpoints remain separate. Closed-status filtering and person scoping still run before deduplication.
- No schema, canonical write path, proposal flow, approval gate or commit behavior changed.
- Tests cover cross-type deduplication, multiple duplicate assertions, deterministic representative selection and distinct predicates.
- Full suite is `131 passed`; ruff, format, mypy and Playwright E2E pass.

### Calibration

1. Keep deduplication keyed by the exact triple; do not infer semantic equivalence between different predicates.
2. Keep `related_ids` as the provenance trail so deduplication does not hide contributing records.
3. Next product gap: evaluate optional temporal fields on Relationship; keep `genogram` experimental until real-fixture review.

## 2026-11-04 - Relationship temporal fields

### Current objective

Model optional valid and transaction time on Relationship and expose it in the genogram, without changing canonical write paths or the approval gate.

### Point of situation

- `relationship.schema.json` previously modelled endpoints but no temporal fields, so a dated relation could only carry time through a separate Assertion.
- The schema now accepts optional `valid_time` and `transaction_time`, reusing the Assertion shapes. Internal structure is still validated when present.
- Both schema copies are byte-identical, and `models.Relationship` mirrors the optional `ValidTime`/`TransactionTime` models.
- `genogram` copies both fields into every relation entry when present; missing values appear as `null`.
- Deduplication remains keyed by the exact triple. The representative supplies temporal fields and `related_ids` keeps provenance; no semantic interval merge is attempted.
- No canonical write path, proposal flow, approval gate or commit behavior changed.
- Tests cover schema acceptance, malformed temporal shapes, genogram output and legacy compatibility.
- Full suite is `134 passed`; ruff, format, mypy and Playwright E2E pass.

### Calibration

1. Reuse Assertion temporal shapes for Relationship; do not invent a second vocabulary.
2. Keep fields optional for legacy archives, but validate their contents when present.
3. Next product gap: real-fixture genogram review; consider whether temporal intervals should affect deduplication or view filtering before promoting the command from experimental.

## 2026-11-04 - genogram temporal review

### Current objective

Review genogram behaviour on a realistic family fixture and decide whether temporal intervals should affect deduplication or view filtering before considering promotion from experimental.

### Point of situation

- The fixture `tests/fixtures/genogram_family.json` models four people, a place, two spouse intervals for the same pair, duplicate Assertion/Relationship parent records, an archived spouse and an unsupported lived-in relation.
- Before this unit, the second spouse interval was only visible through `related_ids`; the singular temporal fields came from the lexically first record.
- Decision: an edge remains one exact `(subject, predicate, object)` triple. Intervals do not split edges and no `--at` filter is added.
- Deduplicated entries now aggregate `valid_times` and `transaction_times` across all contributing records, while singular fields remain on the representative.
- Representative selection is Relationship before Assertion, then latest `transaction_time.recorded_at`, then smallest `record_id`.
- Closed relations are filtered before aggregation, so archived/superseded/rejected intervals are excluded.
- The fixture test validates each record and checks interval aggregation, recency, archived exclusion and unsupported-predicate warnings.
- Full suite is `135 passed`; ruff, format, mypy and Playwright E2E pass.
- No canonical write path, proposal flow, approval gate or commit behavior changed.

### Calibration

1. Keep genogram edges structural; do not split them by temporal interval.
2. Aggregate intervals whenever a representative is chosen so the view does not silently lose history.
3. Defer `--at` until interval-overlap semantics for approximate/open dates are designed.
4. Keep genogram experimental until it is reviewed on real user data, not only synthetic fixtures.

## 2026-11-04 - read-only GUI phase 1

### Current objective

Start the PRD M5 human interface with the smallest useful, safety-preserving slice: browse canonical records without adding any write path.

### Point of situation

- Added `GET /records` with exact type/status filters and a case-insensitive text query over id/type/status/title/name/summary/notes/tags; sorting is deterministic by id then relative path.
- Added `GET /records/<id>` with type/status/visibility, relative canonical file, raw JSON, references and backlinks. Unknown IDs return 404; missing references are marked.
- Malformed record files are surfaced as warnings while valid records remain visible.
- No POST route or canonical write path was added. Home and navigation link to Records.
- Integration tests cover list, filters, detail, missing IDs, no POST route, load errors and references/backlinks. Playwright covers the browse flow after approval.
- Checks: `138 passed`; ruff, format, mypy and Playwright edit/approve/reject/browse pass.
- Timeline/genogram, search/export and visibility filters remain open GUI slices.

### Calibration

1. Keep the browser read-only until proposal-backed editing is designed.
2. Reuse the deterministic archive loader and surface load errors; do not hide malformed records.
3. Treat raw JSON as the source of truth and derive only navigation links.
4. Add visibility filtering with search/export, not as an isolated UI toggle.

## 2026-11-04 - read-only GUI phase 2

### Current objective

Extend the PRD M5 human interface with read-only timeline and experimental genogram pages, without adding any write path or changing the approval gate.

### Point of situation

- Added `GET /timeline` with archive scope by default and `?id=...` for entity, place and collection scopes, reusing `timeline.build_timeline`.
- Timeline rows show valid time, assertion, subject, predicate, object, status, transaction time and deduplicated evidence links to `/records/<id>`. Unknown IDs return 404; malformed records remain load warnings.
- Added `GET /genogram?id=...` reusing `genogram.build_genogram`. Missing input returns 400 with a form; unknown people return 404; known people without relations render an empty view.
- Genogram rows show predicate, direction, subject/object links, supported/unsupported badges, source record, `related_ids`, representative temporal fields and aggregated `valid_times`/`transaction_times`. Experimental status and warnings are explicit.
- Navigation and home link to Timeline and Genogram. Both routes are GET-only with no canonical write path.
- Integration tests cover archive/entity/collection scopes, evidence and record links, unknown IDs, missing genogram input, warnings, supported badges and temporal aggregation. Playwright approves a synthetic relation proposal and exercises both views through the real UI.
- Checks: `142 passed`; ruff, format, mypy and Playwright edit/approve/reject/browse/timeline/genogram pass.
- No canonical write path, proposal flow, approval gate or commit behavior changed.

### Calibration

1. Reuse the deterministic derived-view builders in the HTTP layer.
2. Keep derived views GET-only; do not add POST handlers or hidden write paths.
3. Link back to canonical records instead of duplicating record rendering.
4. Show aggregated temporal intervals alongside the representative interval.
5. Keep genogram experimental until it is reviewed on real user data.

## 2026-11-04 - bilingual human input and Firefox

### Current objective

Make the local web UI comfortably usable by a human for adding a memory, with English/Italian parity, and verify it in Firefox as well as Chromium. Keep canonical writes behind the existing proposal/approval gate.

### Point of situation

- Added `GET /memories/new` and `POST /memories/new`. The form creates a pending Episode proposal with title, episode type, captured date, text, participants, tags and visibility.
- The form validates required text, episode type, visibility, known participant IDs and the full Episode schema before calling `create_pending`. It never writes `data/` and never approves.
- Added `src/storygram/i18n.py` with an English source dictionary and Italian translations, plus per-request language context helpers.
- Added a header EN/IT switch backed by `/lang/en` and `/lang/it`, a `storygram_lang` cookie and a redirect to the current page. `?lang=it` also works for direct links and tests.
- Translated navigation, headings, table headers, buttons, placeholders, status badges, episode types, visibility options and web-originated errors. Canonical IDs, type names and stored JSON stay unchanged.
- Added integration coverage for pending-only creation, approval after form input, known participants, validation errors, English default, Italian rendering and cookie-based switching.
- Extended the Playwright Chromium flow with the Add memory form, Italian home rendering and approval of the generated Episode.
- Added `tests/e2e/firefox.mjs` using system Firefox plus WebDriver/geckodriver; it covers the bilingual home, Add memory form, pending proposal, approval and records search.
- Added `npm run test:e2e:firefox` and `npm run test:e2e:all`; documented the Alpine prerequisites `firefox` and `geckodriver`.
- Checks: `149 passed`; ruff, format and mypy clean; Chromium Playwright flow passed; Firefox WebDriver flow passed.
- Follow-up fix `f416922`: the schema format check now enforces RFC3339 date-time and date values, including `captured_at`, `created_at` and `updated_at`. Regression tests cover invalid dates, timezone-less timestamps and the Add memory form.
- Follow-up `04d0f16`: the Records browser filters by visibility and exports the current filter as JSON, JSON-LD, YAML or Markdown through `GET /export`; invalid formats/visibilities return 400. Integration and Chromium E2E cover both.

### Calibration

1. Keep the Add memory form create-only and behind `create_pending`.
2. Keep English as the default and Italian as an explicit switch; test both.
3. Translate labels, not canonical data.
4. Use system Firefox/geckodriver on Alpine musl; do not rely on Playwright's glibc Firefox build.
5. Re-run both browser flows after changing the layout, forms or language switch.
