# Storygram

Local-first, versionable archive for life stories: episodes, sources, people, places, events, relationships, assertions, conflicts and narratives. The core is deterministic and works offline without an LLM.

## Quickstart

```bash
python -m venv .venv
. .venv/bin/activate
pip install -e ".[dev]"

storygram init ./archive
git init ./archive
storygram validate ./archive
storygram web --archive ./archive --host 0.0.0.0 --port 8080
```

Open `http://localhost:8080`, paste or generate a proposal and review the dry-run before approving. Approval is the only path into `data/`.

## Proposal Workflow

Pending proposals live in `proposals/` and are ignored by Git. Approved proposals are archived under `data/proposals/` and committed.

```bash
storygram proposal new --file proposal.json
storygram proposal list
storygram proposal show proposal:example-1
storygram proposal approve proposal:example-1 --dry-run
storygram proposal approve proposal:example-1
storygram proposal reject proposal:example-1 --reason "needs evidence"
storygram proposal withdraw proposal:example-1 --reason "wrong source"
```

`approve` writes atomically and creates one scoped Git commit by default. Use `--no-commit` to skip Git. The archive must be a Git repository with a clean tracked tree. See [the proposal contract](docs/en/PROPOSAL_CONTRACT.md) for operations, evidence and conflict rules.

Pending proposals can be edited from their detail page in the web UI. Applied, merged, rejected, withdrawn and archived proposals are read-only.

## JSON API for Agents

External agents can create, list, read, edit, generate, reject and withdraw pending proposals through the local JSON API. There is intentionally no approve endpoint: a human must review and approve.

```bash
curl -X POST http://localhost:8080/api/proposals \
  -H 'Content-Type: application/json' \
  --data @proposal.json
```

See [the JSON API guide](docs/en/API.md) for endpoints, status codes and examples.

## Optional Local LLM

The adapter can only create pending proposals. It cannot approve or write canonical data. Use the **Generate** page in the web UI or the CLI.

```bash
ollama serve
ollama pull llama3.2
storygram proposal generate --text "Nonna said she lived near the station." --model llama3.2
storygram proposal generate --file interview.txt --json
```

Configuration: `--provider`, `--url`, `--model`, `$STORYGRAM_LLM_PROVIDER`, `$STORYGRAM_LLM_URL`, `$STORYGRAM_LLM_MODEL` and `$STORYGRAM_LLM_API_KEY`. Ollama also honors `$STORYGRAM_OLLAMA_URL` and `$STORYGRAM_OLLAMA_MODEL`. For an OpenAI-compatible server pass `--provider openai --url http://host:8080 --model qwen3-4b`; keep the key in the environment, not in the repository. Provider failures leave canonical data untouched and show the error in the UI.

## Container

The repository includes `Dockerfile`, `compose.yaml` and an auto-init entrypoint. The image was built and exercised end-to-end through a Docker-compatible host daemon (Podman Engine 5.8.2 via the Docker CLI): non-root start, auto-init, healthcheck, in-container proposal apply, restart/recreation persistence and a host bind mount all passed.

```bash
STORYGRAM_PORT=18080 docker compose -p storygram-test up --build -d
docker compose -p storygram-test ps
# Optional Ollama profile:
docker compose -p storygram-test --profile llm up -d
docker compose -p storygram-test exec ollama ollama pull llama3.2
```

The default image works without Ollama. Data persists in the `storygram-data` volume, the UI listens on port 8080 and the container runs as the non-root `storygram` user (UID/GID 100:101). For a bind mount, create the host directory and chown it to that UID/GID; discover it with `docker run --rm --entrypoint id storygram:local`. Set `STORYGRAM_AUTO_INIT=0` to disable automatic archive/Git initialization. Use a unique project name and port for tests, and clean up only the resources you created.

## Layout

- `data/` canonical reviewed records
- `inbox/` unreviewed imports
- `proposals/` local pending proposals
- `media-manifest/` checksummed media manifests
- `generated/` reproducible derived views
- `schema/` canonical JSON Schemas

## Development

```bash
PYTHONPATH=/data/src python -m pytest -q
ruff check src tests
ruff format --check src tests
mypy src

PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=1 npm install
npm run test:e2e
```

Browser tests use Node Playwright with system Chromium. On Alpine: `apk add chromium nodejs npm`.

## Documentation

- [English guide](docs/en/README.md)
- [JSON API](docs/en/API.md)
- [Guida italiana](docs/it/README.md)
- [README (Italiano)](README.it.md)

## Philosophy

- An Episode is a capture, not a fact; assertions carry evidence.
- Keep `valid_time` separate from `transaction_time`.
- Preserve conflicts explicitly; never auto-resolve.
- Correct by supersession; never overwrite history.
- Archive or supersede; never silently delete.
- Keep the deterministic core LLM-free; AI may only submit reviewable proposals.
