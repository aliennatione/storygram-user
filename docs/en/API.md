# JSON API for Agents

The local web server exposes a small JSON API for submitting and maintaining **pending** proposals. It deliberately has no approve endpoint: only the human UI or CLI can apply a proposal.

Start the server:

```bash
storygram web --archive ./archive --host 0.0.0.0 --port 8080
```

## Rules

- Send `Content-Type: application/json`.
- Proposal IDs must start with `proposal:` and must be URL-encoded in paths.
- The API can create and edit pending proposals only.
- Editing preserves `created_at`, refreshes `updated_at` and cannot change the proposal ID.
- Applied, merged, rejected and archived proposals are read-only.
- Nothing in `data/` changes until a human approves the proposal.
- The API is unauthenticated and intended for a controlled local network.

## List proposals

```http
GET /api/proposals
GET /api/proposals?include_applied=1
```

```json
{
  "ok": true,
  "proposals": [
    {
      "id": "proposal:example-1",
      "status": "proposed",
      "title": "Add a memory",
      "updated_at": "2026-10-30T12:00:00+00:00",
      "operation_count": 1,
      "applied": false
    }
  ]
}
```

## Create a pending proposal

```http
POST /api/proposals
Content-Type: application/json
```

```json
{
  "id": "proposal:agent-1",
  "type": "Proposal",
  "status": "proposed",
  "created_at": "2026-10-30T12:00:00+00:00",
  "updated_at": "2026-10-30T12:00:00+00:00",
  "title": "Agent submission",
  "operations": [
    {
      "op": "create",
      "record_type": "Episode",
      "record": {
        "id": "episode:agent-note",
        "type": "Episode",
        "episode_type": "other",
        "status": "reported",
        "created_at": "2026-10-30T12:00:00+00:00",
        "updated_at": "2026-10-30T12:00:00+00:00"
      }
    }
  ]
}
```

A successful request returns `201`, the saved proposal and a `Location` header. Duplicate IDs return `409`.

## Read one proposal

```http
GET /api/proposals/proposal%3Aagent-1
```

The response includes the proposal, whether it is applied, validation errors from a dry-run plan, preview operations and touched files.

```json
{
  "ok": true,
  "applied": false,
  "proposal": {},
  "validation": {"ok": true, "errors": []},
  "preview": [{"op": "create", "record_type": "Episode"}],
  "files": ["data/episodes/episode_example.json"]
}
```

## Edit a pending proposal

```http
PUT /api/proposals/proposal%3Aagent-1
Content-Type: application/json
```

Send the complete replacement proposal. The `id` must match the path ID. The engine preserves `created_at`, sets `updated_at` to the current time and validates the result against the proposal schema.

Editing an applied or closed proposal returns `409`. Changing the ID returns `400`.

## Errors

```json
{"ok": false, "errors": ["proposal already exists: proposal:agent-1"]}
```

- `400`: invalid JSON, invalid proposal, ID change or empty/invalid body.
- `404`: proposal or route not found.
- `405`: method not allowed.
- `409`: duplicate, already applied or closed proposal.
- `413`: body too large.
- `415`: wrong content type.

There is intentionally no `POST /api/proposals/<id>/approve` endpoint.
