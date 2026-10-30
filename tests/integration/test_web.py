from __future__ import annotations

import json
import threading
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen

from click.testing import CliRunner

from storygram.cli import main
from storygram.web import create_server

NOW = "2026-10-30T12:00:00+00:00"


def proposal(proposal_id: str = "proposal:web-1") -> dict:
    return {
        "id": proposal_id,
        "type": "Proposal",
        "status": "proposed",
        "created_at": NOW,
        "updated_at": NOW,
        "title": "Web proposal",
        "operations": [
            {
                "op": "create",
                "record_type": "Episode",
                "record": {
                    "id": "episode:web-note",
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


def get(url: str) -> tuple[int, str]:
    try:
        with urlopen(url) as response:  # noqa: S310 - local test server
            return response.status, response.read().decode()
    except HTTPError as exc:
        return exc.code, exc.read().decode()


def post(url: str, data: dict[str, str]) -> tuple[int, str]:
    request = Request(url, data=urlencode(data).encode())  # noqa: S310 - local test server
    try:
        with urlopen(request) as response:  # noqa: S310 - local test server
            return response.status, response.read().decode()
    except HTTPError as exc:
        return exc.code, exc.read().decode()


def test_home_and_new_proposal(tmp_path: Path) -> None:
    server, thread, base = start(tmp_path)
    try:
        status, body = get(base + "/")
        assert status == 200
        assert "Storygram" in body
        status, body = post(base + "/proposals/new", {"json": json.dumps(proposal())})
        assert status == 200
        assert "proposal:web-1" in body
        assert "Dry-run preview" in body
        assert (tmp_path / "proposals" / "proposal_web-1.json").exists()
        status, body = get(base + "/proposals")
        assert "proposal:web-1" in body
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def test_web_approve_without_commit_and_reject(tmp_path: Path) -> None:
    server, thread, base = start(tmp_path)
    try:
        post(base + "/proposals/new", {"json": json.dumps(proposal())})
        status, body = post(
            base + f"/proposals/{quote('proposal:web-1', safe='')}/approve",
            {"commit": "no"},
        )
        assert status == 200
        assert "merged" in body
        assert (tmp_path / "data" / "episodes" / "episode_web-note.json").exists()
        assert (tmp_path / "data" / "proposals" / "proposal_web-1.json").exists()

        second = proposal("proposal:web-2")
        post(base + "/proposals/new", {"json": json.dumps(second)})
        status, body = post(
            base + f"/proposals/{quote('proposal:web-2', safe='')}/reject",
            {"reason": "duplicate"},
        )
        assert status == 200
        assert "rejected" in body
        data = json.loads((tmp_path / "proposals" / "proposal_web-2.json").read_text())
        assert data["notes"] == "duplicate"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def test_web_rejects_invalid_json(tmp_path: Path) -> None:
    server, thread, base = start(tmp_path)
    try:
        status, body = post(base + "/proposals/new", {"json": "{not json"})
        assert status == 400
        assert "Invalid JSON" in body
        assert not list((tmp_path / "proposals").glob("*.json"))
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)
