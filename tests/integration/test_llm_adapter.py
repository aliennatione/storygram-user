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
    OpenAICompatibleProvider,
    build_prompt,
    build_provider,
    extract_json,
    provider_config,
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


def test_build_prompt_requires_source_episode_and_evidence() -> None:
    prompt = build_prompt("Maria moved to Turin.", ["person:maria"])
    assert "first operation MUST create exactly one Episode" in prompt
    assert "content" in prompt and "faithful source text" in prompt
    assert "evidence" in prompt
    assert '"evidence":["episode:source-capture"]' in prompt
    assert "person:maria" in prompt
    assert "Maria moved to Turin." in prompt


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


def test_extract_json_strips_thinking_blocks() -> None:
    response = 'Thinking...\n<thinking>{"draft": true}</thinking>\n{"id": "proposal:x"}'
    assert extract_json(response) == {"id": "proposal:x"}


def test_openai_provider_builds_request_and_reads_content(monkeypatch) -> None:
    captured = {}

    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return None

        def read(self):
            return b'{"choices":[{"message":{"content":"{\\"ok\\": true}"}}]}'

    def fake_urlopen(request, timeout):
        captured["url"] = request.full_url
        captured["timeout"] = timeout
        captured["body"] = json.loads(request.data)
        captured["authorization"] = request.headers.get("Authorization")
        return Response()

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
    provider = OpenAICompatibleProvider(
        model="qwen3-4b",
        base_url="http://llm:8080",
        timeout=9,
        api_key="test-key",
    )

    assert provider.complete("hello") == '{"ok": true}'
    assert captured["url"] == "http://llm:8080/v1/chat/completions"
    assert captured["timeout"] == 9
    assert captured["body"]["model"] == "qwen3-4b"
    assert captured["body"]["messages"] == [{"role": "user", "content": "hello"}]
    assert captured["body"]["stream"] is False
    assert captured["authorization"] == "Bearer test-key"


def test_openai_provider_surfaces_http_error_without_leaking_key(monkeypatch) -> None:
    import urllib.error

    def fake_urlopen(request, timeout):
        raise urllib.error.HTTPError(request.full_url, 401, "Unauthorized", {}, None)

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
    provider = OpenAICompatibleProvider(api_key="super-secret")

    with pytest.raises(LLMAdapterError) as excinfo:
        provider.complete("hello")
    assert "HTTP 401" in str(excinfo.value)
    assert "super-secret" not in str(excinfo.value)


def test_provider_config_resolves_env_defaults(monkeypatch) -> None:
    monkeypatch.setenv("STORYGRAM_LLM_PROVIDER", "openai")
    monkeypatch.setenv("STORYGRAM_LLM_MODEL", "qwen3-4b")
    monkeypatch.setenv("STORYGRAM_LLM_URL", "http://llm:8080")
    monkeypatch.setenv("STORYGRAM_LLM_API_KEY", "env-key")

    config = provider_config()
    assert config.provider == "openai"
    assert config.model == "qwen3-4b"
    assert config.base_url == "http://llm:8080"
    assert config.api_key == "env-key"
    assert isinstance(build_provider("openai"), OpenAICompatibleProvider)


def test_provider_config_resolves_timeout_and_token_limits(monkeypatch) -> None:
    monkeypatch.setenv("STORYGRAM_LLM_TIMEOUT", "900")
    monkeypatch.setenv("STORYGRAM_LLM_MAX_TOKENS", "768")
    provider = build_provider("openai")
    assert isinstance(provider, OpenAICompatibleProvider)
    assert provider.timeout == 900
    assert provider.max_tokens == 768


def test_provider_config_rejects_invalid_timeout(monkeypatch) -> None:
    monkeypatch.setenv("STORYGRAM_LLM_TIMEOUT", "slow")
    with pytest.raises(LLMAdapterError, match="must be an integer"):
        build_provider("openai")


def test_provider_config_rejects_unknown_provider() -> None:
    with pytest.raises(LLMAdapterError, match="Unknown LLM provider"):
        provider_config("nope")
