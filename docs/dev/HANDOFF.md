# Session Handoff

Last updated: 2026-11-02
Branch: `feature/agent-proposal-flow`
Recent commits: API/provider/withdraw series, legacy command hardening, then the local GGUF helper/profile commits. Use `git log --oneline -20`.

## Compacted Context

- Storygram is a local-first archive with a tested proposal workflow: agent/CLI/UI creates pending JSON, a human reviews a dry-run, approval applies atomically and commits Git, rejection leaves canonical data untouched.
- Implemented: all 15 schemas, registry-driven validation, atomic apply/rollback, CLI proposal lifecycle, web create/edit/generate/review, JSON API, and Ollama plus OpenAI-compatible providers.
- Agent API can create/list/read/update/generate/reject/withdraw pending proposals. Approval is intentionally UI/CLI-only; there is no approve endpoint and no auto-approval path.
- `withdrawn` is a terminal status alongside `rejected` and `applied`; closing a proposal archives it or marks it without touching canonical data.
- Python baseline: `86 passed`; ruff/format/mypy clean; Playwright edit/approve/reject flow passing.
- Local GGUF helpers are tracked: `scripts/download-model.sh` downloads a checksummed Qwen 1.5B Q4_K_M file, and `scripts/llm-up.sh` starts the `llm` llama.cpp Compose profile with a read-only model mount. The model itself is untracked.
- The container deliverable was rebuilt and re-verified with the live OpenAI-compatible endpoint, then removed. Details and exact results are in `docs/dev/STATE.md` and `docs/dev/AUDIT.md`.
- The 2026-11-01 API/provider/withdraw work and the legacy command hardening are committed in small atomic units.
- Known product debt: `ingest` only copies to `inbox/`; `export` and several legacy views/search commands remain partial; `PRD.md`/`PLAN.md` are not a full description of the shipped proposal workflow.

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
- The qwen3-4b proposal envelope was valid, but its operation records failed `proposal approve --dry-run`; generation does not guarantee an applicable proposal.
- The key was passed through an ephemeral env file and was never committed or logged. Remove the file after use.

## Verified Local GGUF Run (2026-11-02)

- Downloaded model: `models/qwen2.5-1.5b-instruct-q4_k_m.gguf` (about 1.0 GB), SHA256 `6a1a2eb6d15622bf3c96857206351ba97e1af16c30d7a74ee38970e434e9407e`.
- `scripts/download-model.sh` and `scripts/llm-up.sh` are tracked and executable; both pass `sh -n`.
- `llm-up.sh` with a stubbed `docker` derived the host path `/mnt/c/Users/erobi/Desktop/storygram_test/models`, exported `STORYGRAM_LLM_PROVIDER=openai`, `STORYGRAM_LLM_URL=http://llm:8080`, `STORYGRAM_LLM_MODEL=qwen2.5-1.5b-instruct-q4_k_m`, and invoked `compose --profile llm up -d`.
- Real `llm` profile: model loaded in about 2m36s; `/health` returned `{"status":"ok"}`; `/v1/models` listed the GGUF path; the model mount was read-only.
- App container on host port 18080 reached `healthy`; in-container `proposal generate` returned `ok: true` with a valid proposal envelope.
- The 1.5B model ignored most of the prompt and produced a minimal Episode with no evidence/source, so the operation record would fail dry-run. Treat this as a quality limitation, not a wiring defect.
- Containers, project network, project volume and temporary Alpine image from this run were removed. The downloaded model and `storygram:local` remain.
- The Ollama profile is now `--profile ollama`; `--profile llm` is the llama.cpp service.

## Next Objective

The legacy command audit is complete. Continue with the remaining product gaps without redesigning the approval gate.

1. Implement real JSON-LD and YAML/Markdown round-trip export, or explicitly narrow the contract in `PRD.md`/docs.
2. Add capture metadata/checksums to `ingest` while keeping `inbox/` as the only destination.
3. Extend timelines to place/collection/archive level and model Relationship endpoints before promoting `genogram`.
4. Keep approval UI/CLI-only. An advisory, non-applying review endpoint is still open for discussion.
5. Keep the local GGUF helpers honest: they wire inference only; the small model is not a quality baseline.
6. Keep bilingual docs in sync and re-run Python, lint, format, mypy and Playwright checks.

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
- `genogram` is experimental and ignores Relationship records until their schema models endpoints.
- JSON-LD export is a minimal `@id`/`@type` projection, not a full RDF round-trip.
- `ingest` never writes canonical data; review and propose separately.

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
