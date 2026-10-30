# Decisions

## Product and UX

- Primary users are all three groups: the story owner, family collaborators and agents/tools.
- First vertical slice: agent/CLI proposal -> human review -> atomic merge.
- CLI comes before the web UI. The UI is local and served on `0.0.0.0:8080`.
- The LLM adapter comes after the UI and must only produce reviewable proposals.
- The adapter is provider-agnostic: a callable mock for tests and a stdlib Ollama provider for local use.
- Generation and persistence are separate; only `save_pending` touches disk, and only `proposals/`.
- The core remains deterministic and usable offline without an LLM.

## Proposal Model

- Proposals use explicit operations, never arbitrary patches.
- v1 operations: `create`, `update_metadata`, `supersede`, `archive`.
- Operation vocabulary is generic across record types; policy is enforced per type.
- IDs are supplied by the proposal and validated by Storygram.
- Each semantic operation needs evidence. Episode is the explicit exception: it is itself a capture.
- Evidence references must point to Episode, Source or Annotation records.
- Metadata updates are limited to an allowlist. Facts go through Assertions.
- Conflict records are not archived. They have explicit review states instead.
- Applied proposals are archived under `data/proposals/` with status `merged`.
- A potential conflict blocks apply unless the proposal creates or references an explicit Conflict containing both assertions.

## Pending Editing and API

- Pending edits replace the JSON while preserving `created_at` and the proposal ID.
- Only open pending proposals are editable; applied/rejected/archived records are read-only.
- External agents can create, list, read and update pending proposals.
- There is intentionally no API approve endpoint; approval stays human UI/CLI.
- The API is local, unauthenticated and documented as controlled-network only.

## Application and Git

- `approve` applies and commits by default.
- `--dry-run` shows operations and touched files without writing or checking Git.
- `--no-commit` writes atomically but skips Git.
- Default approval requires a clean tracked working tree; untracked/ignored pending proposals do not block it.
- Commit only application files plus the archived proposal, using one scoped commit.
- Any write or commit failure rolls back data files, leaving the pending proposal intact.
- The archived proposal stores `applied_at`; the commit message stores the proposal ID. The resulting hash is returned to the caller rather than written into the same commit.
- Pending proposals under `proposals/` stay ignored and local. Only the merged archive is committed.

## Schema and Validation

- Canonical schemas live in `schema/`; root duplicates are kept byte-identical.
- The assertion schema was corrected: a `superseded` assertion requires `transaction_time.recorded_until`, not `supersedes`. The replacement assertion carries `supersedes`.
- Validation must cover every canonical record type, duplicate IDs and broken references.
- Empty `data/` is valid.
- Tested behavior requires `/data` as the working directory because existing tests use relative paths.

## Conflict Heuristic

- v1 only auto-detects Assertion conflicts with the same subject and predicate but different object/value.
- Validity windows are compared by year; unknown/approximate time overlaps conservatively.
- Closed assertions (`superseded`, `archived`, `rejected`) are ignored.
- This is an apply-time guard, not a complete temporal reasoner.

## Process

- Work in small atomic commits using Conventional Commits.
- Keep this support documentation current and commit it with the work it describes.
- Prefer subagents for inventory/research and direct edits for tightly coupled implementation.
- Do not claim a check passed unless it actually ran in this environment.

## Deployment

- The final deliverable must be containerizable.
- The default container must work fully offline and without Ollama.
- Compose should offer an optional local Ollama profile/service for the LLM adapter.
- The web UI remains exposed on port 8080 with `/data` persisted via a volume/bind mount.
- Containerization comes after Playwright and the LLM adapter so the packaged surface is already tested.
- The runtime image is non-root, offline-capable and has no Chromium/Node; browser tooling stays in development.
- The entrypoint may auto-initialize an empty `/data` and Git repository, but never auto-approves records.
- Ollama is an optional Compose profile; the app still runs and validates without it.
