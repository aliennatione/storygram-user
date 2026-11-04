# Session Handoff

Last updated: 2026-11-04
Branch: `feature/agent-proposal-flow`
Recent commits: API/provider/withdraw series, legacy command hardening, local GGUF helpers, export/import/capture units, then endpoint-aware Relationship records on 2026-11-04. Use `git log --oneline -20`.

## Compacted Context

- Storygram is a local-first archive with a tested proposal workflow: agent/CLI/UI creates pending JSON, a human reviews a dry-run, approval applies atomically and commits Git, rejection leaves canonical data untouched.
- Implemented: all 15 schemas, registry-driven validation, atomic apply/rollback, CLI proposal lifecycle, web create/edit/generate/review, JSON API, and Ollama plus OpenAI-compatible providers.
- Agent API can create/list/read/update/generate/reject/withdraw pending proposals. Approval is intentionally UI/CLI-only; there is no approve endpoint and no auto-approval path.
- `withdrawn` is a terminal status alongside `rejected` and `applied`; closing a proposal archives it or marks it without touching canonical data.
- Python baseline: `124 passed`; ruff/format/mypy clean; Playwright edit/approve/reject flow passing.
- Relationship records now carry an optional all-or-nothing `subject`/`predicate`/`object` triple, and `genogram` reads complete records alongside `relation:*` assertions. It remains experimental.
- Export round-trips are implemented: JSON-LD/YAML/Markdown export plus reversible module parsers and tests. JSON/JSON-LD/YAML are lossless at record level; Markdown uses YAML front matter as source of truth.
- Safe import is implemented: `storygram import FILE` wraps JSON/JSON-LD/YAML/Markdown exports in a schema-validated, create-only pending proposal. It runs the approval dry-run planner before writing and touches only `proposals/`; canonical data still requires human approval.
- Local GGUF helpers are tracked: `scripts/download-model.sh` downloads a checksummed Qwen 1.5B Q4_K_M file by default, and `scripts/llm-up.sh` starts the `llm` llama.cpp Compose profile with a read-only model mount. The model itself is untracked. The 1.5B file is a smoke test; the 3B file is not practical on 1 CPU.
- The container deliverable was rebuilt and re-verified with the live OpenAI-compatible endpoint, then removed. Details and exact results are in `docs/dev/STATE.md` and `docs/dev/AUDIT.md`.
- The 2026-11-01 API/provider/withdraw work and the legacy command hardening are committed in small atomic units.
- Known product debt: media manifest and several legacy views/search commands remain partial; `PRD.md`/`PLAN.md` are not a full description of the shipped proposal workflow.

## Verified Container Run (2026-10-31)

Environment observed through the mounted host socket:

- Docker CLI 29.9.2, Docker Compose v5.6.1.
- Server: Podman Engine 5.8.2 (`linux/amd64`, Fedora 42 host), used through its Docker-compatible API.
- Image `storygram:local` built successfully from `/data`.

Results:

1. Compose started a named-volume instance on host port 18080.
2. Container ran as UID 100 / GID 101 (`storygram`), not root.
3. Auto-init created `/data/data`, all 15 schemas and `/data/.git`; initial schema commit was created.
4. Healthcheck reached `healthy`; HTTP check inside the container returned `http-ok`.
5. In-container proposal flow worked: `proposal new`, `list`, `approve --dry-run`, `approve`; approval created a scoped Git commit.
6. Data survived `restart` and `compose down` (without `-v`) followed by `up`.
7. A host bind mount initialized correctly, served HTTP and persisted after container removal.
8. Test containers, volumes, network and image were removed; only the unrelated `OC-storygram` development container remained.
9. The optional Ollama profile was not run; it stays optional and unverified.

## Verified LLM Run (2026-11-01)

- Endpoint: `http://100.64.0.8:8080/v1/chat/completions`, llama-swap, model `qwen3-4b`; bearer authentication required.
- Provider config is environment-only: `STORYGRAM_LLM_PROVIDER`, `STORYGRAM_LLM_MODEL`, `STORYGRAM_LLM_URL`, `STORYGRAM_LLM_API_KEY`.
- Provider aliases `openai`, `openai-compatible`, `llamacpp`, `llama-swap` and similar all select the OpenAI-compatible adapter; `ollama` remains the default.
- Inside the rebuilt container, `/v1/models` returned 4 models and `proposal generate` returned a saved pending proposal.
- The HTTP API returned `201` for generation, `200` for withdraw and `409` for a second withdraw.
- The earlier qwen3-4b operation records failed `proposal approve --dry-run`. After prompt hardening on 2026-11-02, qwen3-4b passed dry-run on Italian, English and short-capture fixtures; generation still does not guarantee semantic correctness.
- The key was passed through an ephemeral env file and was never committed or logged. Remove the file after use.

## Verified Local GGUF Run (2026-11-02)

- Downloaded model: `models/qwen2.5-1.5b-instruct-q4_k_m.gguf` (about 1.0 GB), SHA256 `6a1a2eb6d15622bf3c96857206351ba97e1af16c30d7a74ee38970e434e9407e`.
- `scripts/download-model.sh` and `scripts/llm-up.sh` are tracked and executable; both pass `sh -n`.
- `llm-up.sh` with a stubbed `docker` derived the host path `/mnt/c/Users/erobi/Desktop/storygram_test/models`, exported `STORYGRAM_LLM_PROVIDER=openai`, `STORYGRAM_LLM_URL=http://llm:8080`, `STORYGRAM_LLM_MODEL=qwen2.5-1.5b-instruct-q4_k_m`, and invoked `compose --profile llm up -d`.
- Real `llm` profile: model loaded in about 2m36s; `/health` returned `{"status":"ok"}`; `/v1/models` listed the GGUF path; the model mount was read-only.
- App container on host port 18080 reached `healthy`; in-container `proposal generate` returned `ok: true` with a valid proposal envelope.
- The hardened prompt made the 1.5B model emit the captured Episode with `content.text`; it passes dry-run but still does not extract people, places or assertions. This is a model-quality limitation, not a schema/wiring failure.
- The 3B GGUF (`qwen2.5-3b-instruct-q4_k_m.gguf`, SHA256 `626b4a6678b86442240e33df819e00132d3ba7dddfe1cdc4fbb18e0a9615c62d`) loaded in about 9 minutes at 1.86 GiB, then produced no token for more than 25 minutes under the 1-CPU quota. It was stopped and is not the default.
- Remote qwen3-4b with the hardened prompt produced six operations and a passing dry-run for the Italian fixture; English passed after adding a literal-value assertion example. A model typo (`place:neapes`) shows human review is still required.
- Do not switch models on the llama-swap server during a session; keep qwen3-4b as the single quality reference.
- Containers, project network, project volume and temporary Alpine image from this run were removed. The downloaded model and `storygram:local` remain.
- The Ollama profile is now `--profile ollama`; `--profile llm` is the llama.cpp service.

## Export Round-Trip Unit (2026-11-03)

- `src/storygram/export.py` now provides `export_yaml`, `export_markdown`, `records_from_yaml`, `records_from_jsonld` and `records_from_markdown`.
- `storygram export --format` accepts `json`, `jsonld`, `yaml` and `markdown`; JSON/JSON-LD output shape is unchanged.
- YAML is a lossless sequence. JSON-LD is reversed from `@graph` nodes via `@id`/`@type` and remains a local projection. Markdown uses start/end markers, moves Episode `content.text` or `notes` into the body and records it in `storygram_body` front matter.
- `tests/integration/test_export_roundtrip.py` covers the smallest Person case, nested Assertion values, Episode text, notes, trailing newlines, multiple records, malformed inputs and CLI output.
- No canonical import command was added: exported records cannot bypass proposals or human approval.
- Checks in this unit: `103 passed`, ruff/format/mypy clean, Playwright edit/approve/reject passed.

## Safe Import Unit (2026-11-03)

- `src/storygram/importer.py` reads an export in JSON, JSON-LD, YAML or Markdown and converts it to a create-only pending proposal.
- `records_from_json` was added to `export.py` so all export formats have a matching parser.
- Import validates every record schema, rejects non-proposable types, duplicate IDs and IDs already canonical, then calls `plan_apply` before writing. A proposal that cannot pass dry-run is rejected and leaves no pending file.
- Evidence: imported Episode/Source/Annotation records are ordered first and attached to later operations that require evidence. `--evidence` adds IDs of captures already in canonical data.
- `import` writes only `proposals/`; it never touches `data/`, never approves and never commits. The normal `proposal approve [--dry-run]` human path is unchanged.
- CLI: `storygram import FILE [--format ...] [--evidence ID ...] [--id PROPOSAL_ID] [--title ...] [--archive PATH] [--json]`.
- Tests: `tests/integration/test_import.py` covers all formats, pending-only writes, post-import approval, evidence wiring, missing evidence, invalid schema, duplicate/existing IDs and format override.
- Checks in this unit: `116 passed`, ruff/format/mypy clean, Playwright edit/approve/reject passed.

## Capture Metadata Unit (2026-11-03)

- `src/storygram/capture.py` copies the capture with a streaming SHA-256 (no second read) and writes `inbox/.storygram/<filename>.json`.
- Sidecar format `storygram.capture/1` records filename, byte size, guessed MIME type, SHA-256 checksum object, `ingested_at` and `overwritten`.
- Capture and sidecar are written to temp files and moved with `os.replace`; a failed metadata write removes a newly replaced capture and any stale sidecar.
- `ingest episode` gained `--json`. Plain output reports size, checksum and sidecar path.
- Inbox or metadata-directory preparation failures raise `CaptureError` with context instead of an unhandled traceback.
- `inbox/` remains the only destination; canonical `data/` is untouched. A sidecar is not a canonical Episode and does not confirm any fact.
- Tests cover checksum/size/MIME, binary content, JSON output, overwrite refresh and refused-overwrite preservation.
- Checks in this unit: `121 passed`, ruff/format/mypy clean, Playwright edit/approve/reject passed.

## Relationship Endpoints Unit (2026-11-04)

- `schema/relationship.schema.json` and its root duplicate now include optional `subject`, `predicate` (`relation:*`) and `object`. The three fields are all-or-nothing via JSON Schema `if`/`then`; a bare legacy Relationship remains valid.
- `models.Relationship` mirrors the optional fields. Schema validation is still the authoritative check.
- `genogram` reads complete Relationship records and `relation:*` assertions, scopes both to the requested person, skips `superseded`/`archived`/`rejected` relations and warns on incomplete Relationship records.
- Genogram entries now include `record_id` and `record_type`; `assertion_id` is preserved for assertions and `relationship_id` is added for Relationship records.
- The generation prompt still forbids Relationship output but no longer says the schema lacks endpoints.
- No canonical write path, approval gate or proposal behavior changed.
- Checks in this unit: `124 passed`, ruff/format/mypy clean, Playwright edit/approve/reject passed.

## Next Objective

The legacy command audit is complete. Continue with the remaining product gaps without redesigning the approval gate.

1. Extend timelines to collection/archive level (place timelines already match object-side assertions). Keep `genogram` experimental until reviewed against real fixtures.
2. Keep approval UI/CLI-only. An advisory, non-applying review endpoint is still open for discussion.
3. Keep the local GGUF helpers honest: they wire inference only. The 1.5B model is a smoke test, the 3B model is impractical on 1 CPU, and qwen3-4b is the single quality reference. Always dry-run generated proposals.
4. Keep bilingual docs in sync and re-run Python, lint, format, mypy and Playwright checks.

## Environment Check

```bash
cd /data
test -S /var/run/docker.sock && echo socket-ok
docker version
docker compose version
docker info --format '{{.ServerVersion}}'
```

If the development container was regenerated, reinstall the toolchain:

```bash
apk add --no-cache python3 py3-pip git nodejs npm chromium docker-cli docker-cli-compose jq
pip install --break-system-packages -e ".[dev]"
```

If the socket is present but the client is missing and package installation is allowed:

```bash
apk add --no-cache docker-cli docker-cli-compose
```

Never start `dockerd`; this is client-to-host-daemon access. Record whether the server is Docker or a Docker-compatible engine such as Podman.

## Container Regression Procedure

Use a unique project name and non-default host port.

```bash
cd /data
docker build -t storygram:local /data
export STORYGRAM_PORT=18080
docker compose -f /data/compose.yaml -p storygram-test up -d
docker compose -f /data/compose.yaml -p storygram-test ps
sleep 30
docker inspect --format '{{.State.Health.Status}}' \
  "$(docker compose -f /data/compose.yaml -p storygram-test ps -q storygram)"
```

Expected: `healthy`. Then verify from inside the container:

```bash
C="docker compose -f /data/compose.yaml -p storygram-test"
$C exec -T storygram id -u
$C exec -T storygram sh -c 'test -f /data/schema/proposal.schema.json && test -f /data/.git/HEAD && echo init-ok'
$C exec -T storygram sh -c 'git -C /data status --porcelain'
$C exec -T storygram python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8080/', timeout=3).read(); print('http-ok')"
```

Expected: UID `100`, `init-ok`, clean Git tree on a fresh volume, `http-ok`.

Persistence:

```bash
$C exec -T storygram sh -c 'printf persistence-ok > /data/proposals/docker-check.txt'
$C restart storygram
$C exec -T storygram cat /data/proposals/docker-check.txt
$C exec -T storygram rm /data/proposals/docker-check.txt
```

For recreation, apply a synthetic proposal, run `docker compose -p storygram-test down` (without `-v`), start it again, and confirm the canonical record and Git commit still exist.

To exercise the LLM pass-through, start Compose with an env file outside the repository:

```bash
STORYGRAM_PORT=18080 docker compose -f /data/compose.yaml \
  --env-file /tmp/opencode/llm.env -p storygram-test up -d
C="docker compose -f /data/compose.yaml -p storygram-test"
$C exec -T storygram storygram proposal generate --archive /data --json
```

The env file must define `STORYGRAM_LLM_PROVIDER=openai`, `STORYGRAM_LLM_MODEL`, `STORYGRAM_LLM_URL` and `STORYGRAM_LLM_API_KEY`. Delete it after the test. Never print the key in logs or commit it.

## Bind-Mount Regression Procedure

Docker resolves bind sources on the host, not inside the development container. The helper below creates a host directory and returns its **host** path; do not pass the helper's `/hosttmp/...` path directly to `-v`.

```bash
cd /data
IMAGE_UID=$(docker run --rm --entrypoint id storygram:local -u)
IMAGE_GID=$(docker run --rm --entrypoint id storygram:local -g)
HOST_ROOT="/tmp/storygram-bind-check"
HELPER_ROOT="/hosttmp/$(basename "$HOST_ROOT")"
docker run --rm -v /tmp:/hosttmp --user 0 --entrypoint sh storygram:local \
  -c "rm -rf '${HELPER_ROOT}' && mkdir -p '${HELPER_ROOT}' && chown -R ${IMAGE_UID}:${IMAGE_GID} '${HELPER_ROOT}'"

docker rm -f storygram-bind-test 2>/dev/null || true
docker run -d --name storygram-bind-test -p 18081:8080 -v "$HOST_ROOT:/data" storygram:local
sleep 8
docker exec storygram-bind-test sh -c 'test -f /data/schema/proposal.schema.json && test -f /data/.git/HEAD && echo bind-init-ok'
docker exec storygram-bind-test python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8080/', timeout=3).read(); print('bind-http-ok')"

docker rm -f storygram-bind-test
docker run --rm -v "$HOST_ROOT:/data" --entrypoint sh storygram:local \
  -c 'test -f /data/schema/proposal.schema.json && test -f /data/.git/HEAD && echo bind-persisted'
docker run --rm -v /tmp:/hosttmp --user 0 --entrypoint sh storygram:local \
  -c "rm -rf '${HELPER_ROOT}'"
```

If the helper cannot create a host path, report the limitation and use the named-volume check as the verified path. Do not substitute a development-container `/data` path.

## Optional Ollama Profile

Only if network/time permit:

```bash
docker compose -f /data/compose.yaml -p storygram-test --profile ollama up -d ollama
docker compose -f /data/compose.yaml -p storygram-test exec -T ollama ollama pull llama3.2
docker compose -f /data/compose.yaml -p storygram-test exec -T storygram \
  storygram proposal generate --text "A synthetic Docker check." --no-save --json
```

A skipped or failed remote pull is not a blocker for the offline container deliverable; record it accurately.

## Defects to Watch

- Named-volume ownership for the non-root user.
- `/data/.git` creation and safe-directory handling.
- Schema discovery via `$STORYGRAM_SCHEMA_DIR=/app/schema`.
- Healthcheck starting too early: the first probe can fail while the UI starts; wait for `healthy`.
- Git author/committer configuration inside the container.
- Compose service DNS: `STORYGRAM_OLLAMA_URL=http://ollama:11434` is only valid with the `ollama` profile; `STORYGRAM_LLM_URL=http://llm:8080` requires the `llm` profile.
- Port conflicts on 8080; always set `STORYGRAM_PORT`. The local `llm` container listens on 8080 inside the Compose network only, but the app publishes 8080 by default.
- The local GGUF takes roughly 2.5 minutes to load on CPU; `/health` and `/v1/models` return 503 until loading finishes. Do not declare the container dead before checking logs.
- `LLAMA_ARG_HOST` is overwritten by the image entrypoint's `--host 0.0.0.0`; the warning is harmless.
- Bind sources must exist on the host daemon. Setting `STORYGRAM_MODELS_DIR=/data/models` inside the development container can fail with a `/data` permission error because that is not the host path; let `llm-up.sh` derive it or pass the real host path.
- Host bind path mismatch with the development container; the helper's `/hosttmp/...` path is not the host path.
- LLM output can be envelope-valid but record-invalid; always dry-run. Never treat generation as approval.
- The API key must stay in the environment; `.env` is gitignored and excluded from the build context.
- `genogram` is experimental. It reads complete endpoint-aware Relationship records and `relation:*` assertions; bare Relationship records produce an incomplete-endpoints warning.
- JSON-LD export is a minimal `@id`/`@type` projection, not a full RDF round-trip; `records_from_jsonld` reverses that projection only.
- Markdown export treats YAML front matter as the source of truth; body-only edits are not re-imported.
- `import` only creates pending proposals; it never writes canonical data. Records that require evidence fail the import unless an imported capture or `--evidence` is supplied.
- Imported evidence records are placed before dependent operations, because `plan_apply` checks evidence against records already created earlier in the same proposal.
- `ingest` writes only the raw capture plus `inbox/.storygram/<filename>.json`; the sidecar is local metadata, not a canonical Episode. Review and propose separately.
- Capture sidecars are overwritten together with the capture only when `--overwrite` is explicit; a refused overwrite leaves both the capture and its metadata unchanged.

## Cleanup

```bash
docker compose -f /data/compose.yaml -p storygram-test down -v
docker rm -f storygram-bind-test 2>/dev/null || true
docker image rm storygram:local 2>/dev/null || true
rm -f /tmp/opencode/llm.env
rm -rf /tmp/opencode/storygram-live /tmp/opencode/storygram-api-live
```

Do not remove unrelated host images, volumes, containers or networks. Do not prune the host daemon. The development container may itself be named with `storygram`; leave it alone.

## Finish Criteria

- Record actual Docker/Compose versions and command results.
- Fix container defects with focused changes; re-run Python and E2E checks after code changes.
- Update `README.md`/`README.it.md` and `docs/en/`/`docs/it/` only with commands actually executed.
- Update `docs/dev/STATE.md`, `DECISIONS.md`, `LESSONS.md` and `AUDIT.md`.
- Commit each coherent unit as a small, atomic local commit; do not push or amend unless explicitly asked.
- End with the standard completion report from `AGENTS.md`.

## New Session Start

The model-quality unit is closed. Start a fresh session from `/data` on branch `feature/agent-proposal-flow`; the only untracked files are known workspace leftovers (`archive/`, `chatgpt.md`, `session-ses_*.md`). Do not reopen model selection unless a regression appears: `qwen3-4b` is the single reference, the 1.5B GGUF is a smoke test, and the 3B GGUF is not promoted.

```bash
cd /data
git status --short --branch
opencode
```

Suggested opening prompt (Italian):

> Riprendi Storygram da `/data`. Leggi `AGENTS.md`, `docs/dev/STATE.md`, `docs/dev/HANDOFF.md`, `docs/dev/DECISIONS.md`, `docs/dev/LESSONS.md` e `docs/dev/AUDIT.md`.
> Conferma branch `feature/agent-proposal-flow` e che non ci siano modifiche tracciate pendenti.
> Il lavoro su `qwen3-4b` e sul prompt è chiuso: non cambiare modello e non cambiare il gate umano.
> Prossimo obiettivo: chiudere il gap di export round-trip JSON-LD/YAML/Markdown richiesto da `PRD.md`, senza rompere l'export JSON. Prima ispeziona PRD e test esistenti, poi proponi un piano atomico e inizia dal caso più piccolo con test di andata/ritorno. Esegui test, ruff, mypy ed E2E, e aggiorna `docs/dev/`.
