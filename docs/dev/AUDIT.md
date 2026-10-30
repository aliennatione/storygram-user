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

1. Commit this feature before exporting the session.
2. Hand off Docker runtime verification and optional editing/API work.
3. Do not claim browser-side Ollama success; only the injected provider path is tested.
