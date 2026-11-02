# Storygram - Implementation Status

`PRD.md` remains the product source of truth. This file records milestone status; do not use it as a substitute for `docs/dev/STATE.md`.

## Milestones

- M0 Git bootstrap + bilingual docs: complete.
- M1 Canonical model + referential integrity: complete.
- M2 Episode/Assertion lifecycle + bitemporal queries: complete for the implemented model.
- M3 Conflict management: complete for explicit conflict records and apply-time guards.
- M4 Git integration (`git-check`): complete.
- M5 Index/search/timeline/genogram: deterministic index/search, filtered timeline and scoped experimental genogram implemented; place/collection/archive-level timelines and endpoint-aware relationships remain open.
- M6 Export JSON/JSON-LD + visibility + media manifest: canonical JSON export is registry-driven, sorted and privacy-safe; JSON-LD is minimal and YAML/Markdown round-trips remain open.
- M7 Proposals/inbox workflow + extended tests: complete proposal workflow; `ingest episode` captures into `inbox/` only and cannot write canonical data.
- M8 Bilingual docs + polish + v0.1.0: complete.
- Post-M8 agent proposal flow: provider-agnostic LLM adapter (Ollama + OpenAI-compatible), web Generate, pending editing, JSON API with create/read/update/generate/reject/withdraw, and Playwright E2E complete. Approval remains UI/CLI-only by design.
- M9 Container runtime verification: complete through the host Docker socket. Image build, non-root start, auto-init, healthcheck, in-container proposal flow, named-volume persistence and host bind mount all passed. The verified daemon was Podman Engine 5.8.2 via its Docker-compatible API. The local `llm` llama.cpp profile was also run with `models/qwen2.5-1.5b-instruct-q4_k_m.gguf`: model load, read-only mount and OpenAI-compatible generation worked. The Ollama profile was not run.

## Deferred Work

1. Clean up the remaining legacy gaps: real JSON-LD/YAML/Markdown round-trips, capture metadata, place/collection/archive-level timelines, and endpoint-aware Relationship records for genograms.
2. Consider an advisory, non-applying model review endpoint; generation/reject/withdraw already exist and approval must stay UI/CLI-only.
3. Run the optional Ollama container profile when network/time permit; it remains unverified. The local `llm` llama.cpp profile is wired and verified, but the small Qwen model produced a schema-invalid Episode and should not be used as a quality baseline.
4. Continue committing each coherent work unit as a small, atomic local commit.

## Git Strategy

- `main` stable, `develop` integration, `feature/*` feature work.
- Conventional Commits.
- Milestone tags `v0.1.0-mX`; release tag `v0.1.0`.

## Documentation

English primary, Italian parallel in `README.it.md`, `docs/en/`, `docs/it/`. Agent working memory lives in `docs/dev/`.
