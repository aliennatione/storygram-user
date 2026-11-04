from __future__ import annotations

import json
import threading
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen

from click.testing import CliRunner

from storygram.cli import main
from storygram.llm import CallableProvider, LLMAdapterError
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


def start(tmp_path: Path, provider_factory=None):
    result = CliRunner().invoke(main, ["init", str(tmp_path)])
    assert result.exit_code == 0, result.output
    server = create_server(tmp_path, host="127.0.0.1", port=0, provider_factory=provider_factory)
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


def write_record(root: Path, directory: str, filename: str, data: dict) -> Path:
    path = root / "data" / directory / filename
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


def person(record_id: str, name: str, status: str = "confirmed") -> dict:
    return {
        "id": record_id,
        "type": "Person",
        "name": name,
        "status": status,
        "created_at": NOW,
        "updated_at": NOW,
    }


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
        assert "Edit pending proposal" in body
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

        third = proposal("proposal:web-3")
        post(base + "/proposals/new", {"json": json.dumps(third)})
        status, body = post(
            base + f"/proposals/{quote('proposal:web-3', safe='')}/withdraw",
            {"reason": "wrong source"},
        )
        assert status == 200
        assert "withdrawn" in body
        data = json.loads((tmp_path / "proposals" / "proposal_web-3.json").read_text())
        assert data["status"] == "withdrawn"
        assert data["notes"] == "wrong source"
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


def test_web_generate_creates_pending_only(tmp_path: Path) -> None:
    captured = {}

    def factory(config):
        captured["model"] = config.model
        captured["url"] = config.base_url
        captured["provider"] = config.provider

        def complete(prompt: str) -> str:
            captured["prompt"] = prompt
            return json.dumps(proposal("proposal:ignored"))

        return CallableProvider(complete)

    server, thread, base = start(tmp_path, factory)
    try:
        status, body = get(base + "/proposals/generate")
        assert status == 200
        assert 'name="source"' in body

        status, body = post(
            base + "/proposals/generate",
            {
                "source": "Nonna said she lived near the station.",
                "model": "test-model",
                "url": "http://test-ollama:11434",
                "provider": "openai",
            },
        )

        assert status == 200
        assert "Dry-run preview" in body
        assert captured["model"] == "test-model"
        assert captured["url"] == "http://test-ollama:11434"
        assert captured["provider"] == "openai"
        assert "Nonna said" in captured["prompt"]
        pending = list((tmp_path / "proposals").glob("*.json"))
        assert len(pending) == 1
        assert not (tmp_path / "data" / "episodes" / "episode_web-note.json").exists()
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def test_web_generate_rejects_empty_source(tmp_path: Path) -> None:
    server, thread, base = start(tmp_path)
    try:
        status, body = post(base + "/proposals/generate", {"source": "   "})
        assert status == 400
        assert "Source text is empty" in body
        assert not list((tmp_path / "proposals").glob("*.json"))
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def test_web_generate_surfaces_provider_error(tmp_path: Path) -> None:
    def factory(config):
        def complete(prompt: str) -> str:
            raise LLMAdapterError("model offline")

        return CallableProvider(complete)

    server, thread, base = start(tmp_path, factory)
    try:
        status, body = post(
            base + "/proposals/generate",
            {"source": "A memory", "model": "missing", "url": "http://missing"},
        )
        assert status == 502
        assert "model offline" in body
        assert not list((tmp_path / "proposals").glob("*.json"))
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def test_web_edits_pending_proposal(tmp_path: Path) -> None:
    server, thread, base = start(tmp_path)
    try:
        post(base + "/proposals/new", {"json": json.dumps(proposal())})
        status, body = get(base + f"/proposals/{quote('proposal:web-1', safe='')}/edit")
        assert status == 200
        assert "Edit proposal" in body
        assert 'name="json"' in body

        edited = proposal()
        edited["title"] = "Edited title"
        status, body = post(
            base + f"/proposals/{quote('proposal:web-1', safe='')}/edit",
            {"json": json.dumps(edited)},
        )
        assert status == 200
        assert "Edited title" in body
        saved = json.loads((tmp_path / "proposals" / "proposal_web-1.json").read_text())
        assert saved["title"] == "Edited title"
        assert saved["created_at"] == NOW

        changed_id = proposal("proposal:web-other")
        status, body = post(
            base + f"/proposals/{quote('proposal:web-1', safe='')}/edit",
            {"json": json.dumps(changed_id)},
        )
        assert status == 400
        assert "id cannot change" in body
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def test_web_cannot_edit_applied_proposal(tmp_path: Path) -> None:
    server, thread, base = start(tmp_path)
    try:
        post(base + "/proposals/new", {"json": json.dumps(proposal())})
        post(
            base + f"/proposals/{quote('proposal:web-1', safe='')}/approve",
            {"commit": "no"},
        )
        status, body = get(base + f"/proposals/{quote('proposal:web-1', safe='')}/edit")
        assert status == 409
        assert "Cannot edit applied proposal" in body

        status, body = post(
            base + f"/proposals/{quote('proposal:web-1', safe='')}/edit",
            {"json": json.dumps(proposal())},
        )
        assert status == 409
        assert "already applied" in body
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def test_web_records_browse_is_read_only(tmp_path: Path) -> None:
    server, thread, base = start(tmp_path)
    try:
        anna_path = write_record(
            tmp_path, "people", "person_anna.json", person("person:anna", "Anna Rossi")
        )
        write_record(
            tmp_path,
            "people",
            "person_bruno.json",
            person("person:bruno", "Bruno Bianchi", "archived"),
        )
        before = anna_path.read_text(encoding="utf-8")

        status, body = get(base + "/records")
        assert status == 200
        assert "Read-only canonical record browser" in body
        assert "person:anna" in body
        assert "person:bruno" in body

        status, body = get(base + "/records?" + urlencode({"type": "Person", "q": "anna"}))
        assert status == 200
        assert "person:anna" in body
        assert "person:bruno" not in body

        status, body = get(base + "/records?" + urlencode({"status": "archived"}))
        assert status == 200
        assert "person:bruno" in body
        assert "person:anna" not in body

        status, body = get(base + "/records/" + quote("person:anna", safe=""))
        assert status == 200
        assert "Anna Rossi" in body
        assert "data/people/person_anna.json" in body
        assert "Record JSON" in body
        assert "&quot;id&quot;: &quot;person:anna&quot;" in body

        status, body = get(base + "/records/" + quote("person:missing", safe=""))
        assert status == 404
        assert "Record not found" in body

        status, body = post(base + "/records", {})
        assert status == 404
        assert anna_path.read_text(encoding="utf-8") == before
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def test_web_records_surface_load_errors(tmp_path: Path) -> None:
    server, thread, base = start(tmp_path)
    try:
        write_record(tmp_path, "people", "person_anna.json", person("person:anna", "Anna Rossi"))
        broken = tmp_path / "data" / "people" / "broken.json"
        broken.write_text("{not json", encoding="utf-8")

        status, body = get(base + "/records")
        assert status == 200
        assert "Some records could not be loaded" in body
        assert "invalid json" in body
        assert "person:anna" in body
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def test_web_record_detail_links_references_and_backlinks(tmp_path: Path) -> None:
    server, thread, base = start(tmp_path)
    try:
        write_record(tmp_path, "people", "person_anna.json", person("person:anna", "Anna Rossi"))
        write_record(
            tmp_path, "people", "person_bruno.json", person("person:bruno", "Bruno Bianchi")
        )
        write_record(
            tmp_path,
            "assertions",
            "assertion_anna_bruno.json",
            {
                "id": "assertion:anna-bruno",
                "type": "Assertion",
                "subject": "person:anna",
                "predicate": "relation:sibling",
                "object": "person:bruno",
                "status": "reported",
                "transaction_time": {"recorded_at": NOW},
                "created_at": NOW,
                "updated_at": NOW,
            },
        )

        status, body = get(base + "/records/" + quote("person:anna", safe=""))
        assert status == 200
        assert "Referenced by" in body
        assert "assertion:anna-bruno" in body

        status, body = get(base + "/records/" + quote("assertion:anna-bruno", safe=""))
        assert status == 200
        assert "References" in body
        assert "person:anna" in body
        assert "person:bruno" in body
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)
