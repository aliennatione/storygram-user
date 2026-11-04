# AGENTS.md

## Project

Storygram is a local-first, file-based archive for life stories. `PRD.md` is the product source of truth; `PLAN.md` is the milestone/status map. The core must stay deterministic and usable offline without an LLM.

Current state: functional MVP for proposals, validation, local web review with a bilingual English/Italian interface, read-only record browsing plus timeline and experimental genogram views, an Add memory form that creates pending Episode proposals, and optional Ollama or OpenAI-compatible generation. The proposal path is tested end-to-end and the container deliverable is runtime-verified through the host Docker socket. Legacy commands are hardened and CLI-tested: `ingest episode` is inbox-only, export/search/rebuild/timeline/conflicts are deterministic, and genogram remains experimental although Relationship records model endpoints and optional temporal fields, equivalent triples are deduplicated, and all temporal intervals are preserved. JSON-LD/YAML/Markdown round-trips are implemented, `import` turns an export into a create-only pending proposal without writing canonical data, and `ingest` writes checksummed capture metadata under `inbox/.storygram/`. Timelines now support entity, place, collection and archive scopes; collection timelines include direct `relation:member_of` members. Verify a command before documenting it as working.

Durable context, in order:
1. `AGENTS.md` - workflow and environment rules.
2. `docs/dev/STATE.md` - branch, completed work, exact next steps and checks.
3. `docs/dev/HANDOFF.md` - compact briefing for the next session.
4. `docs/dev/DECISIONS.md`, `LESSONS.md`, `AUDIT.md` - rationale, quirks and session history.

## Communication

- Address the user in Italian unless they explicitly switch language.
- Keep code, commit messages and English documentation in English; Italian user/contract docs stay in the bilingual files.


## Environment

- Development repository: `/data`, usually bind-mounted from the host.
- Current development image: Alpine, Python 3.14.10, Git, Node/npm, system Chromium and system Firefox/geckodriver for the Firefox smoke test. A fresh image may still lack some tools; install only what the task needs and record it.
- Dependencies are installed with `pip install --break-system-packages -e ".[dev]"`.
- The development container has `/var/run/docker.sock` bind-mounted from the host.
- That socket talks to the **host container daemon**, not Docker-in-Docker. It may be Docker Engine or a Docker-compatible engine such as Podman; read `docker version` instead of assuming. Never start `dockerd`.

Check before Docker work:

```bash
test -S /var/run/docker.sock
docker version
docker compose version
```

If `docker` is missing, install only the client if the session permits it (`apk add docker-cli docker-cli-compose`) and still use the mounted socket. If the socket or CLI is unavailable, stop and report the blocker instead of creating a daemon.

## Commands

Run from `/data`; tests use relative paths such as `schema/episode.schema.json`.

```bash
PYTHONPATH=/data/src python -m pytest -q
PYTHONPATH=/data/src python -m pytest tests/integration/test_api.py -v
PYTHONPATH=/data/src python -m storygram --help
ruff check src tests
ruff format --check src tests
mypy src
npm run test:e2e
npm run test:e2e:firefox
```

- Prefer `PYTHONPATH=/data/src python -m storygram ...` until the package is installed.
- `npm run test:e2e` uses Node Playwright with `/usr/bin/chromium`; Python Playwright is not musllinux-compatible.
- `npm run test:e2e:firefox` uses WebDriver/geckodriver with system `/usr/bin/firefox`; install with `apk add firefox geckodriver`. `npm run test:e2e:all` runs both.
- Current baseline: `146 passed`, ruff/format/mypy clean, Playwright edit/approve/reject/browse/timeline/genogram/add-memory/Italian flows and the Firefox add-memory smoke flow passing.
- Never claim a check passed unless it actually ran in this environment.

## Docker from the Host Socket

Read `docs/dev/HANDOFF.md` before the first Docker command. Key rules:

- The Docker CLI and Compose read the project locally, but images, containers and volumes live on the host daemon.
- The default `compose.yaml` uses the named volume `storygram-data`; it does not require a host bind path.
- `docker build -t storygram:local /data` is safe because the client sends the build context to the daemon.
- A `-v /data/...` path inside the development container is **not** necessarily a valid host path. For bind-mount tests, create a host-side temp directory through a helper container and mount that host path.
- Host-published ports may not be reachable from the development container at `127.0.0.1`. Verify the app from inside the container (`docker compose exec`, health status) and treat host UI access as a separate check.
- Use a unique Compose project name and port (for example `-p storygram-test`, `STORYGRAM_PORT=18080`).
- Do not mount the Docker socket into the Storygram application container.
- The socket is root-equivalent on the host. Never run broad cleanup commands such as `docker system prune`, and only remove resources created for this test.

## Repository Map

- `src/storygram/`: `cli.py`, `web.py`, `i18n.py`, `proposals.py`, `llm.py`, `registry.py`, `validate.py`, `models.py`, `index.py`, `gitcheck.py`, `bitemporal.py`, `conflicts.py`, `export.py`, `importer.py`, `capture.py`, `timeline.py`, `genogram.py`.
- `schema/`: canonical JSON Schemas. Root-level `*.schema.json` duplicates must stay byte-identical with `schema/`.
- `data/`: canonical reviewed records only; currently empty.
- `proposals/`: local pending proposals, gitignored. `data/proposals/` is the committed merged archive.
- `tests/`: unit and integration tests plus synthetic fixtures. `tests/e2e/web.mjs` drives the real local UI.
- `generated/`, `inbox/`, `media-manifest/`, `models/`: gitignored derived, unreviewed or large local data; do not commit.
- `scripts/`: local GGUF download and llama.cpp Compose helpers. The model file itself stays untracked.
- `archive/`, `chatgpt.md`, `session-ses_*.md`, `{src/`: leftovers, not application source.
- `docs/en/`, `docs/it/`: bilingual user/contract/API documentation.
- `docs/dev/`: durable agent working memory.

## CLI and Web Surface

- Implemented and tested: `init`, `get`, `list`, `validate`, `git-check`, `web`, `proposal new|list|show|approve|reject|withdraw|generate`.
- Proposal approval is atomic, creates one scoped Git commit by default, supports `--dry-run` and `--no-commit`.
- The web UI supports a read-only `/records` browser (type/status/text filters, detail with raw JSON and reference/backlink links), read-only `/timeline` (archive/entity/place/collection scopes) and experimental `/genogram` views, an `/memories/new` form that creates pending Episode proposals, create/edit pending proposals, Generate, dry-run, approve and reject. Timeline and genogram are GET-only and cannot write canonical data. The header switches English/Italian via `/lang/en` and `/lang/it`; translations live in `i18n.py`.
- JSON API supports `GET/POST /api/proposals`, `GET/PUT /api/proposals/<id>`, `POST /api/proposals/generate`, `POST /api/proposals/<id>/reject` and `POST /api/proposals/<id>/withdraw`; there is intentionally no approve endpoint.
- `ingest episode` only copies into `inbox/` and writes a SHA-256 capture sidecar; `import` creates a validated create-only pending proposal from an export and never writes canonical data; `export`, `search`, `rebuild`, `timeline` and `conflicts` have focused CLI tests; `timeline` supports entity/place/collection scopes plus `--all`; `genogram` is experimental, reads endpoint-aware Relationship records plus `relation:*` assertions, deduplicates equivalent triples with a `related_ids` list, prefers the most recently recorded Relationship, and exposes representative `valid_time`/`transaction_time` plus aggregated `valid_times`/`transaction_times`.
- `init` copies all 15 schemas through the registry and supports `$STORYGRAM_SCHEMA_DIR`.

## Domain Invariants

These are non-negotiable (details in `PRD.md`):

- An Episode is a capture, not a fact. Ingestion must never auto-confirm an assertion.
- Keep `valid_time` (represented time) separate from `transaction_time` (recorded time). Corrections create new IDs and supersede; never overwrite history.
- Preserve conflicts explicitly with both sides and evidence; never auto-resolve.
- Archive or supersede records; never silently delete or merge people/entities.
- Keep the core deterministic and LLM-free. AI may submit reviewable proposals only.
- Only humans approve; no agent/API path may apply canonical data.
- Use synthetic data only in tests and fixtures.

## Testing and Docs

- Add regression tests for defects and malformed/empty/boundary cases. Do not weaken tests to pass.
- CLI changes need focused CLI tests; HTTP/API changes need integration tests; UI flows need E2E when practical.
- Container runtime is verified (build, non-root, auto-init, healthcheck, proposal flow, named-volume persistence, host bind mount). The optional local `llm` llama.cpp profile and GGUF helpers are runtime-verified; the Ollama profile is not. Re-run the `docs/dev/HANDOFF.md` regression procedure after changing `Dockerfile`, `compose.yaml`, the entrypoint or packaging; a passing Python suite alone does not prove the container works.
- Keep `README.md` / `README.it.md` and `docs/en/` / `docs/it/` in sync.
- Update `docs/dev/STATE.md`, `HANDOFF.md`, `DECISIONS.md`, `LESSONS.md` and `AUDIT.md` at the end of every meaningful work unit.

## Git Conventions

- `main` is stable; `develop` is integration; feature work uses `feature/*`.
- Use Conventional Commits: `feat:`, `fix:`, `docs:`, `test:`, `refactor:`, `chore:`, `ci:`.
- Milestone tags follow `v0.1.0-mX`; release tag `v0.1.0`.
- Commit frequently in small, atomic local commits so work stays traceable. Commit each coherent unit, not one giant commit at the end.
- Stage only intended files. Never commit secrets, real personal data, `generated/` output, unreviewed `inbox/` files, `archive/`, `chatgpt.md` or session notes.
- Do not push, amend, force-push or create tags/releases unless the user explicitly asks. Local commits are allowed and expected.

## Completion Report

End significant work units with:

```text
## Summary
- ...

## Files changed
- ...

## Checks run
- `command`: result

## Assumptions
- ...

## Risks or limitations
- ...

## Next step
- ...
```

When instructions conflict, prioritize safety, privacy, data integrity and the human approval gate over convenience. `PRD.md` is the product authority; `AGENTS.md` is the workflow authority.
