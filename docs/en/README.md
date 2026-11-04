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

The web UI exposes the same engine, including a read-only **Records** browser with type/status/text filters, record detail with raw JSON plus reference and backlink links, a **Generate** page for local/Ollama or OpenAI-compatible models and an edit link for pending proposals:

```bash
storygram web --archive ./archive --host 0.0.0.0 --port 8080
```

The UI is unauthenticated and intended for a controlled local network or container port mapping.

The **Timeline** page builds archive-level or entity/place/collection timelines from open assertions and links each entry to its assertion, records and evidence. The **Genogram** page is an experimental read-only relationship view with supported-predicate badges, warnings, and representative plus aggregated temporal intervals. Neither page has a write route.

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

External agents can create, list, read, update, generate, reject and withdraw pending proposals over HTTP. They cannot approve them. See [API.md](API.md).

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

For an OpenAI-compatible server:

```bash
export STORYGRAM_LLM_PROVIDER=openai
export STORYGRAM_LLM_URL=http://127.0.0.1:8080
export STORYGRAM_LLM_MODEL=qwen3-4b
export STORYGRAM_LLM_API_KEY=...
storygram proposal generate --text "A memory..." --archive ./archive
```

The adapter forces `status=proposed`, drops unknown fields and saves only under `proposals/`. It cannot approve, apply or modify canonical records. Use `--no-save` to inspect without writing. The web **Generate** page uses the same adapter; provider errors are shown without writing anything. Tune generation with `$STORYGRAM_LLM_TIMEOUT` and `$STORYGRAM_LLM_MAX_TOKENS`.

For the bundled local GGUF path:

```bash
scripts/download-model.sh
STORYGRAM_MODELS_DIR=<host-path>/models scripts/llm-up.sh
```

The helpers keep the model outside Git and mount it read-only into the optional `llm` Compose profile. The default 1.5B file is a wiring smoke test; on a 1-CPU container the 3B file is not practical. Use one `qwen3-4b` OpenAI-compatible endpoint as the quality reference and always dry-run generated proposals.

## Legacy and derived commands

These commands are deterministic and offline, but some remain narrower than `PRD.md`:

- `storygram ingest episode FILE [--archive PATH] [--overwrite]` copies a capture into `inbox/` only and writes a checksummed sidecar under `inbox/.storygram/<filename>.json` (`format` `storygram.capture/1`, size, MIME type, SHA-256, `ingested_at`, `overwritten`). It never writes `data/` and refuses silent overwrites; `--json` prints the capture metadata.
- `storygram export [--format json|jsonld|yaml|markdown] [--visibility VALUE ...] [--archive PATH]` reads canonical records through the registry, sorts by ID and fails on malformed JSON. With a visibility filter, records lacking `visibility` are excluded. `jsonld` stays a local `@id`/`@type` graph projection, not full RDF expansion. JSON, JSON-LD and YAML round-trip losslessly (JSON stays the native list); Markdown uses YAML front matter plus a rendered body, so the front matter is the source of truth and body-only edits are not re-imported. There is no direct canonical import: `storygram import` produces a pending proposal, so review and approval still go through proposals.
- `storygram import FILE [--format json|jsonld|yaml|markdown] [--evidence ID ...] [--id PROPOSAL_ID] [--archive PATH]` parses an export and creates a create-only pending proposal. It validates every record schema and runs the same dry-run planner as approval before writing. Imported Episode/Source/Annotation records are wired as evidence for later operations, and `--evidence` can point at captures already in canonical data. Canonical `data/` is never written by the import; review and approval stay human.
- `storygram rebuild [PATH]` rebuilds only the SQLite/FTS5 search index. It is idempotent, drops stale records and reports malformed inputs.
- `storygram search QUERY [--archive PATH] [--rebuild]` matches exact IDs and types first, then indexed content. The index refreshes when canonical files change.
- `storygram conflicts [--status VALUE] [--archive PATH]` merges explicit Conflict records with assertion-derived contradictions, deduplicates pairs and includes both assertions plus evidence.
- `storygram timeline [ID] [--all] [--archive PATH]` excludes superseded, archived and rejected assertions, sorts by valid-time start and includes evidence fields. `ID` covers entity, place and collection timelines; a collection also includes assertions about records that assert `relation:member_of` it. `--all` builds an archive-level timeline.
- `storygram genogram ID [--archive PATH]` is experimental: it reads `relation:*` assertions and endpoint-aware Relationship records, marks unsupported predicates, warns about Relationship records without complete endpoints, deduplicates equivalent Assertion/Relationship triples (preferring the most recently recorded Relationship) while listing every contributing ID in `related_ids`, and exposes temporal data as representative `valid_time`/`transaction_time` plus aggregated `valid_times`/`transaction_times`.

`validate`, `get`, `list` and `git-check` remain the stable read and validation surface.

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
docker compose -p storygram-test --profile ollama up -d
docker compose -p storygram-test exec ollama ollama pull llama3.2
```

The default container auto-initializes `/data` and Git when needed, runs as the non-root `storygram` user (UID/GID 100:101) and persists data in a named volume. For a bind mount, chown the host directory to that UID/GID; discover it with `docker run --rm --entrypoint id storygram:local`. Set `STORYGRAM_AUTO_INIT=0` to opt out. The Ollama profile is optional; the deterministic core and UI work without it. Use a unique project name and port for tests and remove only the resources you create.
