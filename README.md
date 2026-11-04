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

Open `http://localhost:8080`, browse canonical records read-only, then paste or generate a proposal and review the dry-run before approving. Approval is the only path into `data/`.

The **Records** page filters by type, status, visibility or text and opens a read-only detail with raw JSON plus reference and backlink links. The same filters drive JSON, JSON-LD, YAML and Markdown export downloads from `/export`; the page exposes no write route, so canonical changes still require a proposal and human approval.

The **Add memory** form turns free text into a pending Episode proposal with an optional title, date, participants, tags and visibility. It never writes canonical data; approval is still required. The interface is available in English and Italian through the EN/IT switch in the header.

The **Timeline** page renders archive-level or entity/place/collection timelines from open assertions, with links to assertions, records and evidence. The **Genogram** page is an experimental, read-only relationship view with supported-predicate badges, warnings, and both representative and aggregated temporal intervals. Neither page exposes a write route.

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

Configuration: `--provider`, `--url`, `--model`, `$STORYGRAM_LLM_PROVIDER`, `$STORYGRAM_LLM_URL`, `$STORYGRAM_LLM_MODEL` and `$STORYGRAM_LLM_API_KEY`. Tune generation with `$STORYGRAM_LLM_TIMEOUT` and `$STORYGRAM_LLM_MAX_TOKENS`; the Compose `llm` profile also accepts `$STORYGRAM_LLM_CTX_SIZE` (default `8192`). Ollama also honors `$STORYGRAM_OLLAMA_URL` and `$STORYGRAM_OLLAMA_MODEL`. For an OpenAI-compatible server pass `--provider openai --url http://host:8080 --model qwen3-4b`; keep the key in the environment, not in the repository. Provider failures leave canonical data untouched and show the error in the UI.

The bundled GGUF helpers download a small model into `models/` and start the optional `llm` Compose profile:

```bash
scripts/download-model.sh
STORYGRAM_MODELS_DIR=<host-path>/models scripts/llm-up.sh
```

The model is never committed and is mounted read-only into the inference container. `llm-up.sh` derives the host path from the development container when `STORYGRAM_MODELS_DIR` is omitted. The default Qwen2.5-1.5B file is a wiring smoke test, not a quality baseline: it may return only the captured Episode. On a 1-CPU container the 3B file is not recommended (it loaded but produced no tokens within 25 minutes). For quality, use one OpenAI-compatible `qwen3-4b` model as the reference and avoid switching models on the server. Always run `proposal approve --dry-run` before approval.

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

## Container

The repository includes `Dockerfile`, `compose.yaml` and an auto-init entrypoint. The image was built and exercised end-to-end through a Docker-compatible host daemon (Podman Engine 5.8.2 via the Docker CLI): non-root start, auto-init, healthcheck, in-container proposal apply, restart/recreation persistence and a host bind mount all passed.

```bash
STORYGRAM_PORT=18080 docker compose -p storygram-test up --build -d
docker compose -p storygram-test ps
# Optional Ollama profile:
docker compose -p storygram-test --profile ollama up -d
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
npm run test:e2e:firefox
```

Browser tests use Node Playwright with system Chromium for the full flow. The Firefox smoke flow uses WebDriver/geckodriver with system Firefox. On Alpine: `apk add chromium firefox geckodriver nodejs npm`. `npm run test:e2e:all` runs both.

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
