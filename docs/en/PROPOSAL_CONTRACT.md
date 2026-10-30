# Proposal Contract v1

This contract is shared by the CLI, the local web UI, external agents and the LLM adapter.

## Files and Directories

- Pending proposals: `proposals/<name>.json`, ignored by Git.
- Applied proposals: `data/proposals/<name>.json`, committed.
- Canonical records: `data/<type-directory>/<record>.json`.
- Proposal IDs use `proposal:<slug>`.
- Applied proposal IDs must never be reused. Existing archives are not overwritten.

## Proposal Shape

Required fields: `id`, `type` (`Proposal`), `status`, `created_at`, `updated_at`, `operations`.

Useful optional fields: `title`, `target_ids`, `evidence`, `rationale`, `confidence`, `approval_state`, `notes`.

Allowed statuses: `draft`, `proposed`, `under_review`, `approved`, `rejected`, `merged`, `archived`.

Approval is only allowed from `draft`, `proposed`, `under_review` or `approved`. A rejected, merged or archived proposal cannot be approved.

```json
{
  "id": "proposal:example-1",
  "type": "Proposal",
  "status": "proposed",
  "created_at": "2026-10-30T12:00:00+00:00",
  "updated_at": "2026-10-30T12:00:00+00:00",
  "title": "Add a childhood memory",
  "evidence": ["episode:interview-1"],
  "operations": [
    {
      "op": "create",
      "record_type": "Assertion",
      "record": {
        "id": "assertion:home-1990",
        "type": "Assertion",
        "subject": "person:nonna",
        "predicate": "relation:lived_in",
        "object": "place:home",
        "status": "reported",
        "valid_time": {"start": "1990", "end": "1995", "precision": "year"},
        "transaction_time": {"recorded_at": "2026-10-30T12:00:00+00:00"},
        "created_at": "2026-10-30T12:00:00+00:00",
        "updated_at": "2026-10-30T12:00:00+00:00"
      }
    }
  ]
}
```

## Operations

Every operation requires `op` and `record_type`. Record types are the 14 proposable types; Proposal itself is not proposable.

### create

- Requires `record`.
- The record `id` must match `record_type` and must not already exist.
- The full record must pass its schema.
- Evidence is inherited from proposal-level and operation-level `evidence`.

### update_metadata

- Requires `target_id` and non-empty `fields`.
- The target must exist and match `record_type`.
- Only fields in the type's metadata allowlist may be changed.
- `id`, `type` and `created_at` cannot be changed.
- `updated_at` is set by Storygram.
- No evidence is required; this is administrative metadata, not a factual assertion.

### supersede

- Requires `target_id` and `record`.
- Only Episode and Assertion support supersession.
- The replacement must be a new record of the same type and must contain `target_id` in `supersedes`.
- For Assertions, Storygram marks the old record `superseded` and closes its `transaction_time.recorded_until` with the replacement's `transaction_time.recorded_at`.
- The original record is never deleted or overwritten with the replacement.

### archive

- Requires `target_id`.
- Every type except Conflict and Proposal can be archived.
- Archives set `status` to `archived`; they do not delete records.
- Evidence is required only when the type declares `evidence_required`.

## Evidence

- Proposal-level evidence applies to all semantic operations; operation-level evidence is added.
- Evidence must exist in canonical data or be created earlier in the same proposal.
- Only `episode:`, `source:` and `annotation:` references are accepted.
- Assertions created or superseded without evidence are rejected.
- Episode is a capture, so Episode operations do not require separate evidence.

## Conflict Guard

- New or superseded Assertions are compared with all open Assertions.
- Same `subject` and `predicate` with different `object`/`value` and overlapping validity is a potential conflict.
- An explicit Conflict record containing both assertion IDs clears the guard.
- Without that Conflict, approval fails with an error naming both assertions.
- Conflict records use `open`, `under_review`, `resolved`, `accepted_as_plural`, `rejected`.

## Apply Result

A successful approval returns:

```json
{
  "ok": true,
  "proposal_id": "proposal:example-1",
  "dry_run": false,
  "commit": "<git-hash-or-null>",
  "operations": [{"op": "create", "record_type": "Assertion", "record_id": "assertion:home-1990", "evidence": ["episode:interview-1"]}],
  "files": ["data/assertions/assertion_home-1990.json", "data/proposals/proposal_example-1.json"]
}
```

All validation errors are collected before writing. Nothing is written when planning fails.

## Editing Pending Proposals

- Only pending proposals with status `draft`, `proposed`, `under_review` or `approved` can be edited.
- Editing replaces the pending JSON, preserves `created_at`, refreshes `updated_at` and cannot change the proposal ID.
- Applied, merged, rejected and archived proposals are read-only.
- The web edit page, `PUT /api/proposals/<id>` and the pending-update helper all use the same validation and atomic write.

## JSON API Boundary

- `POST /api/proposals` creates a pending proposal.
- `GET /api/proposals` lists pending proposals; `?include_applied=1` also lists the merged archive.
- `GET /api/proposals/<id>` returns the proposal and, for pending proposals, a dry-run validation preview.
- `PUT /api/proposals/<id>` edits a pending proposal.
- There is no approve endpoint. Only the human UI/CLI can apply a proposal.
- The API is local and unauthenticated; expose it only on a controlled network.

## Adapter Boundary

- Adapters receive source text plus optional known canonical IDs and return one proposal.
- Adapters may only create `proposed` proposals; they cannot approve, apply or archive.
- Storygram normalizes adapter output: `type` is `Proposal`, `status` is `proposed`, timestamps are fresh, and unknown top-level fields are dropped.
- `save_pending` validates against the proposal schema and writes only to `proposals/`.
- The web Generate page and CLI call the same adapter and save path; provider failures never touch canonical data.
- The core apply engine remains the only path to canonical data, and it still requires explicit human approval.
- Providers are pluggable. The default Ollama provider calls `/api/generate` with `stream: false` and `format: "json"`.
