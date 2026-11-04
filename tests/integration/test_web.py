from __future__ import annotations

import json
import threading
from http.cookiejar import CookieJar
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import quote, urlencode
from urllib.request import HTTPCookieProcessor, Request, build_opener, urlopen

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


def assertion(
    record_id: str,
    subject: str,
    predicate: str,
    obj: str,
    status: str = "reported",
    start: str = "1987",
    produced_by: list[str] | None = None,
    supported_by: list[str] | None = None,
    transaction_time: dict | None = None,
) -> dict:
    return {
        "id": record_id,
        "type": "Assertion",
        "subject": subject,
        "predicate": predicate,
        "object": obj,
        "status": status,
        "valid_time": {"start": start, "end": None, "precision": "year"},
        "transaction_time": transaction_time or {"recorded_at": NOW, "recorded_until": None},
        "produced_by": produced_by or [],
        "supported_by": supported_by or [],
        "created_at": NOW,
        "updated_at": NOW,
    }


def relationship(
    record_id: str,
    subject: str,
    predicate: str,
    obj: str,
    status: str = "reported",
    valid_time: dict | None = None,
    transaction_time: dict | None = None,
) -> dict:
    data = {
        "id": record_id,
        "type": "Relationship",
        "subject": subject,
        "predicate": predicate,
        "object": obj,
        "status": status,
        "created_at": NOW,
        "updated_at": NOW,
    }
    if valid_time is not None:
        data["valid_time"] = valid_time
    if transaction_time is not None:
        data["transaction_time"] = transaction_time
    return data


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


def test_web_timeline_is_read_only_and_links_records(tmp_path: Path) -> None:
    server, thread, base = start(tmp_path)
    try:
        write_record(tmp_path, "people", "person_anna.json", person("person:anna", "Anna Rossi"))
        write_record(
            tmp_path, "people", "person_bruno.json", person("person:bruno", "Bruno Bianchi")
        )
        write_record(
            tmp_path,
            "episodes",
            "episode_capture.json",
            {
                "id": "episode:capture",
                "type": "Episode",
                "episode_type": "other",
                "status": "reported",
                "created_at": NOW,
                "updated_at": NOW,
            },
        )
        write_record(
            tmp_path,
            "sources",
            "source_album.json",
            {
                "id": "source:album",
                "type": "Source",
                "status": "confirmed",
                "created_at": NOW,
                "updated_at": NOW,
            },
        )
        parent_path = write_record(
            tmp_path,
            "assertions",
            "assertion_parent.json",
            assertion(
                "assertion:parent",
                "person:anna",
                "relation:parent",
                "person:bruno",
                produced_by=["episode:capture"],
                supported_by=["source:album"],
            ),
        )
        write_record(
            tmp_path,
            "assertions",
            "assertion_other.json",
            assertion(
                "assertion:other",
                "person:bruno",
                "relation:lived_in",
                "place:turin",
                start="1990",
            ),
        )
        before = parent_path.read_text(encoding="utf-8")

        status, body = get(base + "/timeline")
        assert status == 200
        assert "Archive timeline" in body
        assert "assertion:parent" in body
        assert "assertion:other" in body
        assert "episode:capture" in body
        assert "source:album" in body
        assert "/records/assertion%3Aparent" in body

        status, body = get(base + "/timeline?" + urlencode({"id": "person:anna"}))
        assert status == 200
        assert "assertion:parent" in body
        assert "assertion:other" not in body
        assert "/records/person%3Aanna" in body

        status, body = get(base + "/timeline?" + urlencode({"id": "person:missing"}))
        assert status == 404
        assert "Unknown record" in body

        status, body = post(base + "/timeline", {})
        assert status == 404
        assert parent_path.read_text(encoding="utf-8") == before
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def test_web_timeline_collection_scope(tmp_path: Path) -> None:
    server, thread, base = start(tmp_path)
    try:
        write_record(
            tmp_path,
            "collections",
            "collection_family.json",
            {
                "id": "collection:family",
                "type": "Collection",
                "name": "Family",
                "status": "confirmed",
                "created_at": NOW,
                "updated_at": NOW,
            },
        )
        write_record(
            tmp_path,
            "assertions",
            "assertion_membership.json",
            assertion(
                "assertion:membership",
                "person:anna",
                "relation:member_of",
                "collection:family",
                start="1980",
            ),
        )
        write_record(
            tmp_path,
            "assertions",
            "assertion_member.json",
            assertion("assertion:member", "person:anna", "relation:lived_in", "place:turin"),
        )
        write_record(
            tmp_path,
            "assertions",
            "assertion_non_member.json",
            assertion(
                "assertion:non-member",
                "person:bruno",
                "relation:lived_in",
                "place:turin",
                start="1990",
            ),
        )

        status, body = get(base + "/timeline?" + urlencode({"id": "collection:family"}))
        assert status == 200
        assert "assertion:membership" in body
        assert "assertion:member" in body
        assert "assertion:non-member" not in body
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def test_web_genogram_shows_relations_warnings_and_temporal_data(tmp_path: Path) -> None:
    server, thread, base = start(tmp_path)
    try:
        write_record(tmp_path, "people", "person_anna.json", person("person:anna", "Anna Rossi"))
        write_record(
            tmp_path, "people", "person_bruno.json", person("person:bruno", "Bruno Bianchi")
        )
        write_record(
            tmp_path,
            "relationships",
            "relationship_parent.json",
            relationship(
                "relationship:parent",
                "person:anna",
                "relation:parent",
                "person:bruno",
                valid_time={"start": "1987", "end": "1995", "precision": "year"},
                transaction_time={"recorded_at": NOW, "recorded_until": None},
            ),
        )
        write_record(
            tmp_path,
            "assertions",
            "assertion_parent.json",
            assertion(
                "assertion:parent",
                "person:anna",
                "relation:parent",
                "person:bruno",
                start="2000",
                transaction_time={
                    "recorded_at": "2026-02-01T00:00:00+00:00",
                    "recorded_until": None,
                },
            ),
        )
        write_record(
            tmp_path,
            "assertions",
            "assertion_lived_in.json",
            assertion(
                "assertion:lived-in",
                "person:anna",
                "relation:lived_in",
                "place:turin",
            ),
        )

        status, body = get(base + "/genogram?" + urlencode({"id": "person:anna"}))
        assert status == 200
        assert "Experimental" in body
        assert "relation:parent" in body
        assert "relation:lived_in" in body
        assert "Unsupported relation predicate: relation:lived_in" in body
        assert '<span class="badge">supported</span>' in body
        assert '<span class="badge">unsupported</span>' in body
        assert "valid_times" in body
        assert "transaction_times" in body
        assert "1987" in body
        assert "2000" in body
        assert "2026-02-01T00:00:00+00:00" in body
        assert "relationship:parent" in body
        assert "assertion:parent" in body
        assert "/records/relationship%3Aparent" in body
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def test_web_genogram_requires_known_person(tmp_path: Path) -> None:
    server, thread, base = start(tmp_path)
    try:
        write_record(tmp_path, "people", "person_anna.json", person("person:anna", "Anna Rossi"))

        status, body = get(base + "/genogram")
        assert status == 400
        assert "Provide a person ID" in body
        assert 'action="/genogram"' in body

        status, body = get(base + "/genogram?" + urlencode({"id": "person:missing"}))
        assert status == 404
        assert "Unknown record" in body

        status, body = get(base + "/genogram?" + urlencode({"id": "person:anna"}))
        assert status == 200
        assert "No relations for person:anna" in body

        status, body = post(base + "/genogram", {})
        assert status == 404
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def test_web_add_memory_creates_pending_episode_proposal(tmp_path: Path) -> None:
    server, thread, base = start(tmp_path)
    try:
        status, body = get(base + "/memories/new")
        assert status == 200
        assert "Add memory" in body
        assert 'action="/memories/new"' in body
        assert 'href="/proposals/new"' in body

        status, body = post(
            base + "/memories/new",
            {
                "title": "Nonna's garden",
                "episode_type": "memory",
                "captured_at": "1987",
                "text": "Nonna said she planted tomatoes every spring.",
                "tags": "family, garden",
                "visibility": "family",
            },
        )
        assert status == 200
        assert "Dry-run preview" in body

        pending = list((tmp_path / "proposals").glob("*.json"))
        assert len(pending) == 1
        proposal = json.loads(pending[0].read_text(encoding="utf-8"))
        assert proposal["status"] == "proposed"
        assert proposal["title"] == "Nonna's garden"
        operation = proposal["operations"][0]
        assert operation["op"] == "create"
        assert operation["record_type"] == "Episode"
        record = operation["record"]
        assert record["type"] == "Episode"
        assert record["episode_type"] == "memory"
        assert record["status"] == "reported"
        assert record["captured_at"] == "1987"
        assert record["content"]["text"] == "Nonna said she planted tomatoes every spring."
        assert record["tags"] == ["family", "garden"]
        assert record["visibility"] == "family"
        assert not list((tmp_path / "data" / "episodes").glob("*.json"))

        status, body = post(
            base + f"/proposals/{quote(proposal['id'], safe='')}/approve",
            {"commit": "no"},
        )
        assert status == 200
        assert "merged" in body
        episode_file = tmp_path / "data" / "episodes" / f"{record['id'].replace(':', '_')}.json"
        assert episode_file.exists()
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def test_web_add_memory_accepts_known_participants(tmp_path: Path) -> None:
    server, thread, base = start(tmp_path)
    try:
        write_record(tmp_path, "people", "person_anna.json", person("person:anna", "Anna Rossi"))

        status, body = post(
            base + "/memories/new",
            {
                "text": "Anna remembered the garden.",
                "participants": "person:anna, person:anna",
            },
        )
        assert status == 200

        pending = list((tmp_path / "proposals").glob("*.json"))
        assert len(pending) == 1
        proposal = json.loads(pending[0].read_text(encoding="utf-8"))
        record = proposal["operations"][0]["record"]
        assert record["participants"] == ["person:anna"]
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def test_web_add_memory_validates_input(tmp_path: Path) -> None:
    server, thread, base = start(tmp_path)
    try:
        status, body = post(base + "/memories/new", {"text": "   "})
        assert status == 400
        assert "Memory text is required" in body
        assert not list((tmp_path / "proposals").glob("*.json"))

        status, body = post(
            base + "/memories/new",
            {"text": "A memory", "episode_type": "invalid"},
        )
        assert status == 400
        assert "Unsupported episode type: invalid" in body
        assert not list((tmp_path / "proposals").glob("*.json"))

        status, body = post(
            base + "/memories/new",
            {"text": "A memory", "participants": "person:missing"},
        )
        assert status == 400
        assert "Unknown participant: person:missing" in body
        assert not list((tmp_path / "proposals").glob("*.json"))

        status, body = post(
            base + "/memories/new",
            {"text": "A memory", "captured_at": "not-a-date"},
        )
        assert status == 400
        assert "schema validation error" in body
        assert not list((tmp_path / "proposals").glob("*.json"))
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def test_web_interface_switches_between_english_and_italian(tmp_path: Path) -> None:
    server, thread, base = start(tmp_path)
    try:
        status, body = get(base + "/?lang=it")
        assert status == 200
        assert '<html lang="it">' in body
        assert "Aggiungi memoria" in body
        assert "Coda di revisione" in body
        assert "Cronologia" in body
        assert 'href="/lang/it?next=' in body

        status, body = get(base + "/?lang=en")
        assert status == 200
        assert '<html lang="en">' in body
        assert "Add memory" in body
        assert "Review queue" in body

        status, body = post(base + "/memories/new?lang=it", {"text": ""})
        assert status == 400
        assert "Il testo della memoria è obbligatorio" in body

        jar = CookieJar()
        opener = build_opener(HTTPCookieProcessor(jar))
        with opener.open(base + "/lang/it?next=/records") as response:
            body = response.read().decode()
        assert "Aggiungi memoria" in body
        with opener.open(base + "/memories/new") as response:
            body = response.read().decode()
        assert "Salva proposta in attesa" in body
        assert 'name="text"' in body
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)
