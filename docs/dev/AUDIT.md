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
