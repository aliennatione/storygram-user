# Decisions

## Product and UX

- Primary users are all three groups: the story owner, family collaborators and agents/tools.
- First vertical slice: agent/CLI proposal -> human review -> atomic merge.
- CLI comes before the web UI. The UI is local and served on `0.0.0.0:8080`.
- The LLM adapter comes after the UI and must only produce reviewable proposals.
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
