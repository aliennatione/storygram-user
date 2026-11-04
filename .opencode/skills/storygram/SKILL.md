---
name: storygram
description: Use when working with a Storygram archive: creating or reviewing proposals, querying records, timelines, genograms, conflicts, export/import, and capture. Covers the deterministic CLI and web UI workflow. Do NOT use to approve canonical data or bypass human review.
---

# Storygram Agent Skill

Storygram is a local-first, file-based archive for life stories. The core is deterministic and LLM-free. AI may only submit reviewable proposals; approval is human-only.

## Guardrails

- Never write to `data/`, `proposals/` application logic, or `inbox/` directly except via CLI.
- All writes go through proposals. Never approve, auto-approve, or simulate approval.
- Always run `proposal approve <id> --dry-run` before any human approval.
- Use synthetic data only in tests and examples.
- Keep `valid_time` separate from `transaction_time`.
- Preserve conflicts; never auto-resolve.
- Corrections create new IDs and supersede; never overwrite history.

## Core commands

```bash
storygram init <archive>
storygram validate <archive>
storygram get <id> [--archive <path>]
storygram list [--type <type>] [--archive <path>]
storygram search <query> [--archive <path>]
storygram export [--format json|jsonld|yaml|markdown] [--archive <path>]
storygram import <file> [--format ...] [--evidence <id> ...] [--archive <path>]
storygram timeline <id> [--all] [--archive <path>]
storygram genogram <person-id> [--archive <path>]
storygram conflicts [--status <status>] [--archive <path>]
storygram ingest episode <file> [--archive <path>] [--overwrite]
storygram media add <file> [--uri <uri>] [--archive <path>]
storygram media list [--json]
```

## Proposal workflow

```bash
storygram proposal new --file <proposal.json> [--archive <path>]
storygram proposal list [--archive <path>]
storygram proposal show <id> [--json] [--archive <path>]
storygram proposal approve <id> --dry-run [--archive <path>]
storygram proposal approve <id> [--no-commit] [--archive <path>]
storygram proposal reject <id> --reason "<text>" [--archive <path>]
storygram proposal withdraw <id> --reason "<text>" [--archive <path>]
storygram proposal generate --text "<text>" [--provider ...] [--model ...] [--url ...] [--no-save] [--json]
```

## Proposal JSON shape

A proposal has `id`, `title`, `created_at`, `created_by`, `status: proposed`, `operations`, and optional `evidence`. Each operation uses `create`, `update`, `supersede`, `archive`, or `merge`, with `record` and `metadata`. IDs must be lowercase and unique. Evidence must reference existing records.

## Web UI

- `storygram web --archive <path> --host 0.0.0.0 --port 8080`
- Routes: `/records`, `/timeline`, `/genogram`, `/conflicts`, `/memories/new`, `/sources/new`, `/entities/new`, `/people/new`, `/relationships/new`, `/assertions/new`.
- All browser writes create pending proposals only. Approval remains UI/CLI-only.

## JSON API

- `GET/POST /api/proposals`
- `GET/PUT /api/proposals/<id>`
- `POST /api/proposals/generate`
- `POST /api/proposals/<id>/reject`
- `POST /api/proposals/<id>/withdraw`
- No approve endpoint by design.

## Invariants to respect

- An Episode is a capture, not a fact.
- Keep `valid_time` (represented time) separate from `transaction_time` (recorded time).
- Preserve conflicts explicitly; never auto-resolve.
- Archive or supersede records; never silently delete or merge people/entities.
- Keep the core deterministic and LLM-free. AI may submit reviewable proposals only.
- Only humans approve.

## When to use this skill

Use when the user asks about Storygram archives, proposals, records, timelines, genograms, conflicts, export/import, capture, or media. Do not use for unrelated projects.