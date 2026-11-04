# Storygram - Implementation Status

`PRD.md` remains the product source of truth. This file records milestone status; do not use it as a substitute for `docs/dev/STATE.md`.

## Milestones

- M0 Git bootstrap + bilingual docs: complete.
- M1 Canonical model + referential integrity: complete.
- M2 Episode/Assertion lifecycle + bitemporal queries: complete for the implemented model.
- M3 Conflict management: complete for explicit conflict records and apply-time guards.
- M4 Git integration (`git-check`): complete.
- M5 Index/search/timeline/genogram: deterministic index/search, filtered entity/place/collection/archive timelines and scoped experimental genogram implemented; Relationship records carry optional endpoint triples plus optional valid/transaction time; genogram reads complete ones, deduplicates equivalent triples, selects the most recently recorded Relationship as representative and aggregates all temporal intervals. Collection timelines include records that assert `relation:member_of` the collection.
- M5 Human interface (read-only slice): record list with type/status/text filters, detail with raw JSON and reference/backlink links, and load-error warnings; no write route. Timeline, genogram, search/export and visibility filters in the browser remain open.
- M6 Export JSON/JSON-LD/YAML/Markdown + visibility + media manifest: canonical JSON export is registry-driven, sorted and privacy-safe; JSON-LD stays a local graph projection, and JSON-LD/YAML/Markdown now have reversible module parsers with round-trip tests, and `storygram import` turns an export into a dry-run-validated, create-only pending proposal without writing canonical data. Markdown body edits are not re-imported. Media manifest is still open.
- M7 Proposals/inbox workflow + extended tests: complete proposal workflow; `ingest episode` captures into `inbox/` only, writes a SHA-256 metadata sidecar and cannot write canonical data.
- M8 Bilingual docs + polish + v0.1.0: complete.
- Post-M8 agent proposal flow: provider-agnostic LLM adapter (Ollama + OpenAI-compatible), web Generate, pending editing, JSON API with create/read/update/generate/reject/withdraw, and Playwright E2E complete. Approval remains UI/CLI-only by design.
- M9 Container runtime verification: complete through the host Docker socket. Image build, non-root start, auto-init, healthcheck, in-container proposal flow, named-volume persistence and host bind mount all passed. The verified daemon was Podman Engine 5.8.2 via its Docker-compatible API. The local `llm` llama.cpp profile was also run with `models/qwen2.5-1.5b-instruct-q4_k_m.gguf`: model load, read-only mount and OpenAI-compatible generation worked. The Ollama profile was not run. Later prompt work made `qwen3-4b` proposals dry-run valid. The 1.5B local model remains a smoke test; the 3B GGUF was not promoted because it produced no tokens within 25 minutes under a 1-CPU quota.

## Deferred Work

1. Keep `genogram` experimental until reviewed on real user data; duplicate representations are deduplicated, temporal intervals are aggregated without splitting edges, and timeline scopes are complete for the current model.
2. Consider an advisory, non-applying model review endpoint; generation/reject/withdraw already exist and approval must stay UI/CLI-only.
3. Run the optional Ollama container profile when network/time permit; it remains unverified. The local `llm` llama.cpp profile is wired and verified, but the 1.5B Qwen model is only a smoke test and the 3B model is impractical on 1 CPU. Use a single `qwen3-4b` OpenAI-compatible endpoint as the quality reference.
4. Continue committing each coherent work unit as a small, atomic local commit.

## Git Strategy

- `main` stable, `develop` integration, `feature/*` feature work.
- Conventional Commits.
- Milestone tags `v0.1.0-mX`; release tag `v0.1.0`.

## Documentation

English primary, Italian parallel in `README.it.md`, `docs/en/`, `docs/it/`. Agent working memory lives in `docs/dev/`.
