from __future__ import annotations

import json
import threading
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import quote
from urllib.request import Request, urlopen

from click.testing import CliRunner

from storygram.cli import main
from storygram.proposals import apply_proposal
from storygram.web import create_server

NOW = "2026-10-30T12:00:00+00:00"


def proposal(proposal_id: str = "proposal:api-1", title: str = "API proposal") -> dict:
    return {
        "id": proposal_id,
        "type": "Proposal",
        "status": "proposed",
        "created_at": NOW,
        "updated_at": NOW,
        "title": title,
        "operations": [
            {
                "op": "create",
                "record_type": "Episode",
                "record": {
                    "id": "episode:api-note",
                    "type": "Episode",
                    "episode_type": "other",
                    "status": "reported",
                    "created_at": NOW,
                    "updated_at": NOW,
                },
            }
        ],
    }


def start(tmp_path: Path):
    result = CliRunner().invoke(main, ["init", str(tmp_path)])
    assert result.exit_code == 0, result.output
    server = create_server(tmp_path, host="127.0.0.1", port=0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, thread, f"http://127.0.0.1:{server.server_port}"


def request(
    base: str,
    path: str,
    *,
    method: str = "GET",
    body: object | None = None,
    content_type: str = "application/json",
    raw: str | None = None,
) -> tuple[int, dict]:
    data = raw.encode() if raw is not None else None
    if body is not None:
        data = json.dumps(body).encode()
    headers = {"Content-Type": content_type} if data is not None else {}
    req = Request(base + path, data=data, method=method, headers=headers)  # noqa: S310
    try:
        with urlopen(req) as response:  # noqa: S310 - local test server
            return response.status, json.loads(response.read().decode())
    except HTTPError as exc:
        return exc.code, json.loads(exc.read().decode())


def api_proposal(proposal_id: str = "proposal:api-1") -> str:
    return f"/api/proposals/{quote(proposal_id, safe='')}"


def test_api_create_read_and_update(tmp_path: Path) -> None:
    server, thread, base = start(tmp_path)
    try:
        status, payload = request(base, "/api/proposals", method="POST", body=proposal())
        assert status == 201
        assert payload["ok"] is True
        assert payload["location"] == api_proposal()
        assert (tmp_path / "proposals" / "proposal_api-1.json").exists()
        assert not (tmp_path / "data" / "episodes" / "episode_api-note.json").exists()

        status, payload = request(base, "/api/proposals")
        assert status == 200
        assert [item["id"] for item in payload["proposals"]] == ["proposal:api-1"]

        status, payload = request(base, api_proposal())
        assert status == 200
        assert payload["applied"] is False
        assert payload["validation"]["ok"] is True
        assert payload["preview"][0]["op"] == "create"
        assert payload["files"] == [
            "data/episodes/episode_api-note.json",
            "data/proposals/proposal_api-1.json",
        ]

        edited = proposal(title="Edited through API")
        status, payload = request(base, api_proposal(), method="PUT", body=edited)
        assert status == 200
        assert payload["proposal"]["title"] == "Edited through API"
        assert payload["proposal"]["created_at"] == NOW
        assert (tmp_path / "proposals" / "proposal_api-1.json").exists()

        changed_id = proposal("proposal:api-2")
        status, payload = request(base, api_proposal(), method="PUT", body=changed_id)
        assert status == 400
        assert "id cannot change" in payload["errors"][0]
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def test_api_duplicate_not_found_and_closed_status(tmp_path: Path) -> None:
    server, thread, base = start(tmp_path)
    try:
        request(base, "/api/proposals", method="POST", body=proposal())
        status, payload = request(base, "/api/proposals", method="POST", body=proposal())
        assert status == 409
        assert "already exists" in payload["errors"][0]

        status, payload = request(
            base, api_proposal("proposal:missing"), method="PUT", body=proposal()
        )
        assert status == 404
        assert "not found" in payload["errors"][0]

        closed = proposal("proposal:api-closed")
        closed["status"] = "merged"
        status, payload = request(base, "/api/proposals", method="POST", body=closed)
        assert status == 409
        assert "merged" in payload["errors"][0]
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def test_api_rejects_bad_requests_and_has_no_approve_endpoint(tmp_path: Path) -> None:
    server, thread, base = start(tmp_path)
    try:
        status, payload = request(base, "/api/proposals", method="POST", raw="{bad")
        assert status == 400
        assert "Invalid JSON" in payload["errors"][0]

        status, payload = request(
            base, "/api/proposals", method="POST", body=proposal(), content_type="text/plain"
        )
        assert status == 415
        assert "application/json" in payload["errors"][0]

        status, payload = request(base, "/api/proposals", method="POST", raw="[]")
        assert status == 400
        assert "JSON object" in payload["errors"][0]

        request(base, "/api/proposals", method="POST", body=proposal())
        status, payload = request(
            base, f"/api/proposals/{quote('proposal:api-1', safe='')}/approve", method="POST"
        )
        assert status == 404
        assert payload["ok"] is False
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def test_api_marks_applied_proposals_read_only(tmp_path: Path) -> None:
    server, thread, base = start(tmp_path)
    try:
        request(base, "/api/proposals", method="POST", body=proposal())
        apply_proposal(tmp_path, "proposal:api-1", commit=False, now=NOW)

        status, payload = request(base, api_proposal())
        assert status == 200
        assert payload["applied"] is True

        status, payload = request(base, "/api/proposals?include_applied=1", method="GET")
        assert status == 200
        assert payload["proposals"][0]["applied"] is True

        status, payload = request(base, api_proposal(), method="PUT", body=proposal())
        assert status == 409
        assert "already applied" in payload["errors"][0]
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)
