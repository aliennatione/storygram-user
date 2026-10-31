# Storygram Guide

Storygram is a local-first, file-based archive. Canonical records are JSON files under `data/`. Proposed changes are reviewed before they become canonical.

## Requirements

- Python 3.12+
- Git for the default commit-on-approval workflow
- Optional: Docker, local Ollama, Node Playwright for browser tests

## Install

```bash
python -m venv .venv
. .venv/bin/activate
pip install -e ".[dev]"
```

The repository also supports a packaged wheel. Set `STORYGRAM_SCHEMA_DIR` if the installed package cannot locate `schema/`.

## Create and validate an archive

```bash
storygram init ./archive
storygram validate ./archive
storygram list --archive ./archive
```

`init` creates every canonical directory and copies all 15 schemas. It does not initialize Git; run `git init ./archive` yourself if you want commit-on-approval.

## Review a proposal

```bash
storygram proposal new --file proposal.json --archive ./archive
storygram proposal show proposal:example-1 --archive ./archive
storygram proposal approve proposal:example-1 --archive ./archive --dry-run
storygram proposal approve proposal:example-1 --archive ./archive
```

The web UI exposes the same engine, including a **Generate** page for local Ollama and an edit link for pending proposals:

```bash
storygram web --archive ./archive --host 0.0.0.0 --port 8080
```

The UI is unauthenticated and intended for a controlled local network or container port mapping.

## Proposal rules

- Operations are `create`, `update_metadata`, `supersede` and `archive`.
- Semantic changes require evidence from Episode, Source or Annotation records.
- Metadata edits use a per-type allowlist; facts belong in Assertions.
- A superseded Assertion closes `transaction_time.recorded_until`; the replacement carries `supersedes`.
- Potential assertion conflicts block apply until an explicit Conflict record contains both IDs.
- Applied proposals are archived with status `merged`; pending proposals remain local and ignored.
- Approval is atomic, with rollback on write/commit failure.

See `PROPOSAL_CONTRACT.md` in this directory for the full contract.

## JSON API

External agents can create, list, read and update pending proposals over HTTP. They cannot approve them. See [API.md](API.md).

```bash
curl -X POST http://localhost:8080/api/proposals \
  -H 'Content-Type: application/json' \
  --data @proposal.json
```

## Optional LLM generation

```bash
ollama serve
ollama pull llama3.2
storygram proposal generate --text "A memory..." --model llama3.2 --archive ./archive
```

The adapter forces `status=proposed`, drops unknown fields and saves only under `proposals/`. It cannot approve, apply or modify canonical records. Use `--no-save` to inspect without writing. The web **Generate** page uses the same adapter; provider errors are shown without writing anything.

## Tests

```bash
PYTHONPATH=/data/src python -m pytest -q
ruff check src tests
ruff format --check src tests
mypy src
npm run test:e2e
```

`npm run test:e2e` drives the real local server with Playwright and system Chromium. Python Playwright is not usable on Alpine musl; Node Playwright is the supported path there.

## Container

`Dockerfile` and `compose.yaml` are included. The image was verified end-to-end through a Docker-compatible host daemon (Podman Engine 5.8.2 via the Docker CLI): non-root start, auto-init, healthcheck, in-container proposal apply, restart/recreation persistence and a host bind mount all passed.

```bash
STORYGRAM_PORT=18080 docker compose -p storygram-test up --build -d
docker compose -p storygram-test ps
docker compose -p storygram-test --profile llm up -d
docker compose -p storygram-test exec ollama ollama pull llama3.2
```

The default container auto-initializes `/data` and Git when needed, runs as the non-root `storygram` user (UID/GID 100:101) and persists data in a named volume. For a bind mount, chown the host directory to that UID/GID; discover it with `docker run --rm --entrypoint id storygram:local`. Set `STORYGRAM_AUTO_INIT=0` to opt out. The Ollama profile is optional; the deterministic core and UI work without it. Use a unique project name and port for tests and remove only the resources you create.
