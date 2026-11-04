# Decisions

## Product and UX

- Primary users are all three groups: the story owner, family collaborators and agents/tools.
- First vertical slice: agent/CLI proposal -> human review -> atomic merge.
- CLI comes before the web UI. The UI is local and served on `0.0.0.0:8080`.
- The LLM adapter comes after the UI and must only produce reviewable proposals.
- The adapter is provider-agnostic: a callable mock for tests and a stdlib Ollama provider for local use.
- Generation and persistence are separate; only `save_pending` touches disk, and only `proposals/`.
- The core remains deterministic and usable offline without an LLM.

## Proposal Model

- Proposals use explicit operations, never arbitrary patches.
- v1 operations: `create`, `update_metadata`, `supersede`, `archive`.
- Operation vocabulary is generic across record types; policy is enforced per type.
- IDs are supplied by the proposal and validated by Storygram.
- Each semantic operation needs evidence. Episode is the explicit exception: it is itself a capture.
- Evidence references must point to Episode, Source or Annotation records.
- Metadata updates are limited to an allowlist. Facts go through Assertions.
- Conflict records are not archived. They have explicit review states instead.
- Applied proposals are archived under `data/proposals/` with status `merged`.
- A potential conflict blocks apply unless the proposal creates or references an explicit Conflict containing both assertions.

## Pending Editing and API

- Pending edits replace the JSON while preserving `created_at` and the proposal ID.
- Only open pending proposals are editable; applied/rejected/archived records are read-only.
- External agents can create, list, read and update pending proposals.
- There is intentionally no API approve endpoint; approval stays human UI/CLI.
- The API is local, unauthenticated and documented as controlled-network only.

## Application and Git

- `approve` applies and commits by default.
- `--dry-run` shows operations and touched files without writing or checking Git.
- `--no-commit` writes atomically but skips Git.
- Default approval requires a clean tracked working tree; untracked/ignored pending proposals do not block it.
- Commit only application files plus the archived proposal, using one scoped commit.
- Any write or commit failure rolls back data files, leaving the pending proposal intact.
- The archived proposal stores `applied_at`; the commit message stores the proposal ID. The resulting hash is returned to the caller rather than written into the same commit.
- Pending proposals under `proposals/` stay ignored and local. Only the merged archive is committed.

## Schema and Validation

- Canonical schemas live in `schema/`; root duplicates are kept byte-identical.
- The assertion schema was corrected: a `superseded` assertion requires `transaction_time.recorded_until`, not `supersedes`. The replacement assertion carries `supersedes`.
- Validation must cover every canonical record type, duplicate IDs and broken references.
- Empty `data/` is valid.
- Tested behavior requires `/data` as the working directory because existing tests use relative paths.

## Conflict Heuristic

- v1 only auto-detects Assertion conflicts with the same subject and predicate but different object/value.
- Validity windows are compared by year; unknown/approximate time overlaps conservatively.
- Closed assertions (`superseded`, `archived`, `rejected`) are ignored.
- This is an apply-time guard, not a complete temporal reasoner.

## Process

- Work in small atomic commits using Conventional Commits. Local commits are expected after each coherent unit so work stays traceable.
- Do not push, amend, force-push or create tags/releases unless the user explicitly asks.
- Keep this support documentation current and commit it with the work it describes.
- Prefer subagents for inventory/research and direct edits for tightly coupled implementation.
- Do not claim a check passed unless it actually ran in this environment.

## Deployment Verification

- Container verification runs from a development container with the host Docker socket bind-mounted at `/var/run/docker.sock`.
- This is client-to-host-daemon access, not Docker-in-Docker. Never start `dockerd` and never mount the socket into the Storygram application container.
- Docker images, containers and volumes live on the host; build contexts are sent by the client, so building from `/data` works.
- Compose bind-mount sources resolve on the host, not in the development container. Default verification uses the named volume; host bind verification uses a host temp directory created through a helper container.
- Host-published ports are not assumed reachable from the development container. Verify with `docker compose exec` and health status first.
- Verification uses a unique Compose project name and port, and removes only resources it created.

## Deployment

- The final deliverable must be containerizable.
- The default container must work fully offline and without Ollama.
- Compose should offer an optional local Ollama profile/service for the LLM adapter.
- The web UI remains exposed on port 8080 with `/data` persisted via a volume/bind mount.
- Containerization comes after Playwright and the LLM adapter so the packaged surface is already tested.
- The runtime image is non-root, offline-capable and has no Chromium/Node; browser tooling stays in development.
- The entrypoint may auto-initialize an empty `/data` and Git repository, but never auto-approves records.
- Ollama is an optional Compose profile; the app still runs and validates without it.

## Container Verification Result

- The container deliverable is verified through the host socket with Docker CLI 29.9.2 and Compose v5.6.1 against Podman Engine 5.8.2's Docker-compatible API.
- "Docker verified" in project docs means the CLI/Compose workflow passed against a Docker-compatible daemon; future runs must name the actual engine when it is Podman.
- The image runs as UID/GID 100:101 (`storygram`), not 1000. User docs must state the real UID/GID and show how to discover it.
- Host bind paths must be created on the host. A helper container that mounts host `/tmp` at `/hosttmp` returns a container path; map it back to `/tmp/...` before passing it to `-v`.
- The named volume remains the primary persistence check. Restart and `down`/`up` (without `-v`) both preserve canonical records and Git history.
- The Ollama profile stays optional and unverified until a model pull is explicitly run.
- Test resources use a unique Compose project name and host port, then are removed individually; the development container is never removed.

## Proposal Close and API Endpoints (2026-11-01)

- Added `withdrawn` as a terminal proposal status distinct from `rejected` and `applied`.
- `rejected` means the human declined the proposal; `withdrawn` means the submitter or reviewer retracted it. Both preserve the proposal and evidence.
- Closing is centralized: missing proposals map to 404, already closed proposals to 409, success to the new status.
- The JSON API now supports generation, reject and withdraw. It still has **no approve endpoint**.
- Auto-approval was explicitly rejected, including the suggestion to let an LLM classify and apply its own proposals. Generation, classification and advisory review may be automated; applying canonical data may not.
- API close endpoints accept an optional JSON body so a client can supply a reason without a required schema.
- `POST /api/proposals/generate` returns 201 when a proposal is saved and 200 when `save: false`; provider failures return 502.
- API and UI share the same proposal engine. No route bypasses dry-run, validation, archival or Git commit behavior.

## OpenAI-Compatible Provider (2026-11-01)

- The adapter supports both Ollama and any OpenAI-compatible `/v1/chat/completions` endpoint.
- Provider selection is environment-first: `STORYGRAM_LLM_PROVIDER`, `STORYGRAM_LLM_MODEL`, `STORYGRAM_LLM_URL`, `STORYGRAM_LLM_API_KEY`; legacy `STORYGRAM_OLLAMA_*` variables still work.
- The API key comes only from the environment or `--api-key`; it is never written to proposals, logs or the repository.
- The default provider remains `ollama`, preserving the offline-first default.
- OpenAI-compatible aliases cover the common llama.cpp/llama-swap spellings so users do not need to remember one exact name.
- The adapter strips thinking blocks before JSON extraction because reasoning models may emit them before the payload.
- Prompt changes add lowercase ID requirements, `record_type` and a minimal valid proposal shape. The goal is fewer schema-invalid proposals, not automated approval.
- Compose passes the LLM variables into the container. `.env` stays gitignored and excluded from the build context; secrets are supplied at runtime.
- Generation validates the proposal envelope, not every operation record. A dry-run remains the authoritative pre-approval check.

## Legacy Command Hardening (2026-11-01)

- `ingest` now uses the PRD grammar `ingest episode FILE` and writes only to `inbox/`. The previous `--data` option violated the human approval boundary and was removed.
- Ingest refuses to overwrite a same-name capture unless `--overwrite` is explicit. Captures remain unreviewed input, not canonical records.
- Export uses `RECORD_TYPES` instead of a duplicated directory list, sorts by ID and fails on malformed JSON instead of silently omitting data.
- A visibility filter is default-deny: records without a `visibility` field are excluded when the filter is active. An unfiltered export still includes them.
- JSON-LD export emits `@id` and `@type` for every node and a local `@vocab` context. It is explicitly a minimal projection, not a full RDF round-trip.
- The search index is rebuilt from scratch on each rebuild. An FTS5 table has no primary-key uniqueness, so `REPLACE` accumulated duplicates; dropping and recreating removes the ambiguity and stale records.
- Search matches exact IDs, then exact types, then FTS content, then a `LIKE` fallback. Results are sorted by ID. A signature of path/mtime/size refreshes a stale index before searching.
- `rebuild` now advertises only the search index. It exits non-zero and reports malformed records instead of claiming success after silently skipping them.
- Conflicts combine explicit records and assertion-derived contradictions. Derived entries are marked `derived: true`, deduplicated by unordered assertion pair, and carry both assertion records and evidence.
- Derived conflicts use a `derived:` display ID rather than pretending to be canonical `conflict:` records.
- Timeline excludes superseded, archived and rejected assertions, sorts by valid-time start then ID, and includes evidence and transaction fields.
- Timeline distinguishes an unknown record from a known record with no entries; both are actionable errors or explicit empty results.
- Genogram remains experimental. Relationship records are ignored because the schema has no endpoints; relations come from `relation:*` assertions and unsupported predicates are warnings.
- `get` and `list` accept `--archive`, matching the documented examples and the rest of the read surface.

## Local GGUF Helpers and Profiles (2026-11-02)

- The optional Ollama service now uses the `ollama` profile; the `llm` profile is reserved for the local llama.cpp service.
- `scripts/download-model.sh` downloads a specific Qwen 2.5 1.5B Instruct Q4_K_M GGUF and verifies its SHA256. The model stays in the gitignored `models/` directory and is never committed.
- `scripts/llm-up.sh` starts the `llm` profile through Compose. It sets the app to the OpenAI-compatible adapter at `http://llm:8080` and keeps the model file name as the model identifier.
- `STORYGRAM_MODELS_DIR` is the canonical model-directory variable; `download-model.sh` still accepts the older `STORYGRAM_MODEL_DIR` as a fallback.
- The model directory is a host bind source. Inside the development container, `llm-up.sh` derives the host path from the `/data` mount instead of passing the container path to the host daemon.
- The model mount is read-only; inference has no reason to write to the model directory.
- The helper verifies a model only when it is visible locally or at the configured path. A host path that is not visible from the development container cannot be checked; Compose still handles it on the host side.
- Local inference is optional. The core stays deterministic and LLM-free, and generation cannot approve or apply data.

## Local Model Quality and Prompt Contract (2026-11-02)

- `qwen3-4b` is the single quality reference. The server should keep it loaded; do not switch to 8B or 14B during normal review, because model loading adds latency and makes evaluations incomparable.
- The local Qwen 1.5B GGUF remains a transport/wiring smoke test. The local 3B GGUF is not the default and is not recommended on the current 1-CPU quota: it loaded but produced no token in more than 25 minutes.
- The prompt is part of the generation contract, not a cosmetic hint. It must require: an Episode with `content.text`, evidence on operations, no `Relationship` records, `relation:*` predicates, `transaction_time.recorded_at` as record time, source dates in `valid_time`, no `Period` records, only IDs created in the proposal or known, literal facts in `value` without an invented object prefix, and no invented surnames.
- Field-level examples are more effective than prohibitions alone. The literal-value Assertion example made `qwen3-4b` stop emitting `occupation:nurse` as an object.
- Generation validates the proposal envelope, not operation schemas or semantics. A passing generation is not a passing dry-run, and a passing dry-run is not truth. Humans must run `proposal approve --dry-run` and review the result.
- Keep the approval gate unchanged: no approve API endpoint and no auto-apply path.
- `STORYGRAM_LLM_TIMEOUT`, `STORYGRAM_LLM_MAX_TOKENS` and the Compose `STORYGRAM_LLM_CTX_SIZE` are the supported generation controls.

## Export Round-Trips (2026-11-03)

- JSON export remains the canonical machine-readable list and its shape is unchanged.
- YAML export is a `safe_dump` sequence parsed by `safe_load`; this preserves strings, including ISO timestamps, and nested objects. The parser also accepts a single mapping or `{records: [...]}` for hand-edited input.
- JSON-LD remains the existing local `@context`/`@graph` projection. Round-trip parity comes from reversing `@id`/`@type` only; full RDF expansion/compaction is out of scope and documented as such.
- Markdown is a set of blocks delimited by `<!-- storygram:record -->` / `<!-- /storygram:record -->` with YAML front matter and a rendered body. Episode `content.text` and record `notes` live in the body; `storygram_body` records which field was moved. The front matter is the source of truth, so body-only edits are intentionally not re-imported; the end marker keeps body trailing newlines exact.
- Round-trip support lives in module parsers and is tested through export output. No CLI canonical import was added: imported data must still enter through proposals so the human approval gate cannot be bypassed.
- The smallest round-trip case is a single Person; nested Assertion time objects and multiple records are covered to catch serialization regressions.

## Safe Import (2026-11-03)

- Import never writes canonical data. `storygram import` converts an export into a create-only pending proposal under `proposals/`; applying it still requires the normal human `proposal approve` path.
- Every imported record is validated against its schema, and the whole generated proposal is run through `plan_apply` before the pending file is written. An export that would fail dry-run does not produce a pending proposal.
- Only proposable record types can be imported. Proposal records are rejected, as are duplicate IDs within the export and IDs already present in canonical data.
- Imported Episode/Source/Annotation records are ordered before dependent operations and attached as operation-level evidence. Proposal-level evidence is avoided because `plan_apply` validates it for every operation, including before a newly created capture exists.
- `--evidence` lets the reviewer attach already-canonical capture IDs when the export contains only derived records.
- Format is inferred from the suffix (`.json`, `.jsonld`, `.yaml`/`.yml`, `.md`/`.markdown`); `--format` overrides it for ambiguous files.
- The proposal ID defaults to `proposal:import-<file-stem>` and is overridable. Import never auto-approves, never commits and never closes a proposal.
- `records_from_json` completes the parser set for the native JSON export list and accepts a single record or `{records: [...]}` for hand-edited input.

## Capture Metadata (2026-11-03)

- `ingest episode` remains inbox-only. Capture metadata is a hidden sidecar under `inbox/.storygram/`, not a canonical record and not an Episode.
- The checksum is computed while streaming the source into a temp capture, so it describes the exact bytes that are moved into `inbox/` without reading the source twice.
- Sidecars use the versioned format identifier `storygram.capture/1` with filename, byte size, best-effort MIME type, SHA-256, `ingested_at` and `overwritten`. No absolute host paths are stored.
- Capture and sidecar are written to same-directory temp files and moved with `os.replace`. If metadata cannot be moved into place after the capture, the new capture and any stale sidecar are removed and the command fails.
- A refused overwrite leaves both the capture and its metadata unchanged. `--overwrite` refreshes both and records `overwritten: true`.
- `--json` makes the metadata machine-readable; plain output reports size, checksum and sidecar path.
- The sidecar is deliberately not registered as a canonical schema/type. Capture metadata supports later review; it does not confirm facts or write canonical data.
- MIME type is best-effort from the filename and may be `null`; it is informational, not a validation gate.

## Relationship Endpoints (2026-11-04)

- A Relationship now models an optional endpoint triple: `subject`, `predicate` (`relation:*`) and `object`. This reuses the Assertion vocabulary so genogram code and reviewers do not need a second relation language.
- The fields are optional but all-or-nothing. A record with any endpoint field must provide all three. This keeps bare legacy Relationship records valid while preventing half-modelled links.
- Relationship remains a distinct canonical type rather than being folded into Assertion: it can be referenced as an entity, while Assertions remain propositions about entities, events or relationships.
- `genogram` now reads complete Relationship records and `relation:*` assertions. It scopes both to the requested person, skips closed relations and warns about unsupported predicates and incomplete Relationship records.
- Output keeps the existing `assertion_id` key for assertions, adds `relationship_id` for Relationship records, and always includes `record_id` and `record_type`. This preserves existing consumers while making the source explicit.
- Genogram stays experimental. Endpoint modelling is a prerequisite, not a promotion: duplicate representations, temporal validity and real-fixture review remain open.
- Generation continues to prefer Assertions. The prompt no longer states that Relationship has no endpoints, but still forbids model-generated Relationship records to keep the proposal path conservative.
- This is a read-only product increment: no canonical write, proposal, approval or commit behavior changed.
