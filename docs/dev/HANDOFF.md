# Session Handoff

Last updated: 2026-10-31
Branch: `feature/agent-proposal-flow`
Recent commits: `d2851e2` user-facing container docs, `3abf1f0` working-memory update, `493965b` commit policy, `387d775` policy alignment.

## Compacted Context

- Storygram is a local-first archive with a tested proposal workflow: agent/CLI/UI creates pending JSON, a human reviews a dry-run, approval applies atomically and commits Git, rejection leaves canonical data untouched.
- Implemented: all 15 schemas, registry-driven validation, atomic apply/rollback, CLI proposal lifecycle, web create/edit/generate/review, JSON API, optional Ollama adapter.
- Agent API can create/list/read/update pending proposals only. Approval is intentionally UI/CLI-only.
- Python baseline: `51 passed`; ruff/format/mypy clean; Playwright edit/approve/reject flow passing.
- The container deliverable is now verified end-to-end through a Docker-compatible host daemon. Details and exact results are in `docs/dev/STATE.md` and `docs/dev/AUDIT.md`.
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

## Next Objective

Move to the deferred product work now that runtime verification passes. Do not redesign the approval gate.

1. Audit `ingest`, `export`, `search`, `rebuild`, `timeline`, `genogram` and `conflicts` against `PRD.md` and actual behavior.
2. For each command: fix, implement the missing contract, or explicitly mark it experimental in CLI help and bilingual docs. Verify before documenting.
3. Decide whether agents need withdraw/reject or generation API endpoints. Keep approval UI/CLI-only.
4. Keep `README.md` / `README.it.md` and `docs/en/` / `docs/it/` in sync.
5. Re-run Python, lint, format, mypy and Playwright checks after changes.

## Environment Check

```bash
cd /data
test -S /var/run/docker.sock && echo socket-ok
docker version
docker compose version
docker info --format '{{.ServerVersion}}'
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
docker compose -f /data/compose.yaml -p storygram-test --profile llm up -d ollama
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
- Compose service DNS: `STORYGRAM_OLLAMA_URL=http://ollama:11434` is only valid with the `llm` profile.
- Port conflicts on 8080; always set `STORYGRAM_PORT`.
- Host bind path mismatch with the development container; the helper's `/hosttmp/...` path is not the host path.

## Cleanup

```bash
docker compose -f /data/compose.yaml -p storygram-test down -v
docker rm -f storygram-bind-test 2>/dev/null || true
docker image rm storygram:local 2>/dev/null || true
```

Do not remove unrelated host images, volumes, containers or networks. Do not prune the host daemon. The development container may itself be named with `storygram`; leave it alone.

## Finish Criteria

- Record actual Docker/Compose versions and command results.
- Fix container defects with focused changes; re-run Python and E2E checks after code changes.
- Update `README.md`/`README.it.md` and `docs/en/`/`docs/it/` only with commands actually executed.
- Update `docs/dev/STATE.md`, `DECISIONS.md`, `LESSONS.md` and `AUDIT.md`.
- Commit each coherent unit as a small, atomic local commit; do not push or amend unless explicitly asked.
- End with the standard completion report from `AGENTS.md`.
