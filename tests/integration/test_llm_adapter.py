from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from storygram.llm import (
    CallableProvider,
    LLMAdapter,
    LLMAdapterError,
    OllamaProvider,
    extract_json,
    save_pending,
)
from storygram.proposals import apply_proposal

NOW = "2026-10-30T12:00:00+00:00"


def make_archive(tmp_path: Path) -> Path:
    shutil.copytree(Path("schema"), tmp_path / "schema")
    (tmp_path / "proposals").mkdir()
    (tmp_path / "data" / "episodes").mkdir(parents=True)
    (tmp_path / "data" / "proposals").mkdir(parents=True)
    return tmp_path


def generated() -> dict:
    return {
        "id": "ignored:by-normalizer",
        "type": "Proposal",
        "status": "merged",
        "title": "Generated memory",
        "operations": [
            {
                "op": "create",
                "record_type": "Episode",
                "record": {
                    "id": "episode:llm-note",
                    "type": "Episode",
                    "episode_type": "other",
                    "status": "reported",
                    "created_at": NOW,
                    "updated_at": NOW,
                },
            }
        ],
        "unexpected": "dropped",
    }


def adapter(response: str, captured: list[str] | None = None) -> LLMAdapter:
    def complete(prompt: str) -> str:
        if captured is not None:
            captured.append(prompt)
        return response

    return LLMAdapter(
        CallableProvider(complete),
        now=lambda: NOW,
        id_factory=lambda: "proposal:llm-test",
    )


def test_adapter_generates_proposal_and_drops_unknown_fields(tmp_path: Path) -> None:
    root = make_archive(tmp_path)
    captured: list[str] = []
    proposal = adapter("```json\n" + json.dumps(generated()) + "\n```", captured).generate(
        root, "Nonna said she lived near the station.", known_ids=["person:nonna"]
    )

    assert proposal["id"] == "proposal:llm-test"
    assert proposal["type"] == "Proposal"
    assert proposal["status"] == "proposed"
    assert proposal["created_at"] == NOW
    assert "unexpected" not in proposal
    assert "person:nonna" in captured[0]
    assert "Nonna said" in captured[0]


def test_adapter_output_only_creates_pending_until_approved(tmp_path: Path) -> None:
    root = make_archive(tmp_path)
    proposal = adapter(json.dumps(generated())).generate(root, "source")

    path = save_pending(root, proposal)

    assert path == root / "proposals" / "proposal_llm-test.json"
    assert path.exists()
    assert not (root / "data" / "episodes" / "episode_llm-note.json").exists()
    assert not (root / "data" / "proposals" / "proposal_llm-test.json").exists()

    apply_proposal(root, "proposal:llm-test", commit=False, now=NOW)

    assert (root / "data" / "episodes" / "episode_llm-note.json").exists()
    assert not path.exists()


def test_adapter_rejects_duplicate_pending_id(tmp_path: Path) -> None:
    root = make_archive(tmp_path)
    proposal = adapter(json.dumps(generated())).generate(root, "source")
    save_pending(root, proposal)

    with pytest.raises(LLMAdapterError, match="already exists"):
        save_pending(root, proposal)


def test_adapter_rejects_non_json_response(tmp_path: Path) -> None:
    root = make_archive(tmp_path)
    with pytest.raises(LLMAdapterError, match="did not contain"):
        adapter("I cannot do that").generate(root, "source")


def test_adapter_rejects_empty_source(tmp_path: Path) -> None:
    root = make_archive(tmp_path)
    with pytest.raises(LLMAdapterError, match="empty"):
        adapter(json.dumps(generated())).generate(root, "   ")


def test_extract_json_handles_surrounding_text() -> None:
    assert extract_json('prefix {"id": "proposal:x"} suffix') == {"id": "proposal:x"}


def test_ollama_provider_builds_expected_request(monkeypatch) -> None:
    captured = {}

    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return None

        def read(self):
            return b'{"response":"{\\"ok\\": true}"}'

    def fake_urlopen(request, timeout):
        captured["url"] = request.full_url
        captured["timeout"] = timeout
        captured["body"] = json.loads(request.data)
        return Response()

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
    provider = OllamaProvider(model="test-model", base_url="http://ollama:11434", timeout=7)

    assert provider.complete("hello") == '{"ok": true}'
    assert captured["url"] == "http://ollama:11434/api/generate"
    assert captured["timeout"] == 7
    assert captured["body"]["model"] == "test-model"
    assert captured["body"]["stream"] is False
    assert captured["body"]["format"] == "json"
