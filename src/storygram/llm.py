"""Provider-agnostic proposal generation.

Adapters may only create pending proposals. They never write canonical data and
never approve their own output.
"""

from __future__ import annotations

import contextlib
import json
import os
import re
import urllib.error
import urllib.request
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Protocol

from . import proposals as proposals_mod
from . import validate as validate_mod
from .registry import TYPE_BY_NAME, iter_reference_strings

DEFAULT_PROVIDER = "ollama"
DEFAULT_OLLAMA_MODEL = "llama3.2"
DEFAULT_OLLAMA_URL = "http://127.0.0.1:11434"
DEFAULT_OPENAI_MODEL = "qwen3-4b"
DEFAULT_OPENAI_URL = "http://127.0.0.1:8080"
DEFAULT_LLAMACPP_MODEL = DEFAULT_OPENAI_MODEL
DEFAULT_LLAMACPP_URL = DEFAULT_OPENAI_URL
OPENAI_ALIASES = {
    "openai",
    "openai-compatible",
    "openai_compatible",
    "llamacpp",
    "llama.cpp",
    "llama-cpp",
    "llama-swap",
    "llamaswap",
}
OLLAMA_ALIASES = {"ollama"}


class LLMAdapterError(Exception):
    """Raised when a provider response cannot become a valid proposal."""


class Provider(Protocol):
    def complete(self, prompt: str) -> str:
        """Return the provider's raw text response."""


@dataclass
class CallableProvider:
    """Small provider wrapper useful for tests and local integrations."""

    function: Callable[[str], str]

    def complete(self, prompt: str) -> str:
        return self.function(prompt)


@dataclass
class OllamaProvider:
    """Minimal Ollama client using only the standard library."""

    model: str = "llama3.2"
    base_url: str = "http://127.0.0.1:11434"
    timeout: int = 120

    def complete(self, prompt: str) -> str:
        payload = json.dumps(
            {"model": self.model, "prompt": prompt, "stream": False, "format": "json"}
        ).encode()
        request = urllib.request.Request(
            f"{self.base_url.rstrip('/')}/api/generate",
            data=payload,
            headers={"Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                data = json.loads(response.read().decode())
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            raise LLMAdapterError(f"Ollama request failed: {exc}") from exc
        output = data.get("response")
        if not isinstance(output, str):
            raise LLMAdapterError("Ollama response did not contain text")
        return output


@dataclass
class OpenAICompatibleProvider:
    """OpenAI-compatible chat completions client using only the stdlib."""

    model: str = DEFAULT_OPENAI_MODEL
    base_url: str = DEFAULT_OPENAI_URL
    timeout: int = 300
    max_tokens: int = 2048
    temperature: float = 0.1
    api_key: str | None = field(default=None, repr=False)
    completion_path: str = "/v1/chat/completions"

    def complete(self, prompt: str) -> str:
        payload = json.dumps(
            {
                "model": self.model,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": self.temperature,
                "max_tokens": self.max_tokens,
                "stream": False,
            }
        ).encode()
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        request = urllib.request.Request(
            f"{self.base_url.rstrip('/')}{self.completion_path}",
            data=payload,
            headers=headers,
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                data = json.loads(response.read().decode())
        except urllib.error.HTTPError as exc:
            detail = ""
            with contextlib.suppress(Exception):
                detail = exc.read().decode()[:300]
            suffix = f": {detail}" if detail else ""
            raise LLMAdapterError(f"LLM request failed: HTTP {exc.code}{suffix}") from exc
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            raise LLMAdapterError(f"LLM request failed: {exc}") from exc
        choices = data.get("choices")
        if not isinstance(choices, list) or not choices:
            raise LLMAdapterError("LLM response did not contain choices")
        first = choices[0]
        message = first.get("message") if isinstance(first, dict) else None
        output = message.get("content") if isinstance(message, dict) else None
        if not isinstance(output, str):
            raise LLMAdapterError("LLM response did not contain text")
        return output


LlamaCppProvider = OpenAICompatibleProvider


@dataclass
class ProviderConfig:
    """Resolved provider settings for a generation request."""

    provider: str = DEFAULT_PROVIDER
    model: str = ""
    base_url: str = ""
    api_key: str | None = field(default=None, repr=False)


def provider_defaults(provider: str) -> tuple[str, str]:
    """Return the default model and URL for a provider name."""
    name = provider.strip().lower()
    if name in OPENAI_ALIASES:
        return DEFAULT_OPENAI_MODEL, DEFAULT_OPENAI_URL
    if name in OLLAMA_ALIASES:
        return DEFAULT_OLLAMA_MODEL, DEFAULT_OLLAMA_URL
    raise LLMAdapterError(f"Unknown LLM provider: {provider}")


def provider_config(
    provider: str | None = None,
    model: str | None = None,
    base_url: str | None = None,
    api_key: str | None = None,
) -> ProviderConfig:
    """Resolve provider settings from arguments and environment variables."""
    raw_name = provider or os.environ.get("STORYGRAM_LLM_PROVIDER") or DEFAULT_PROVIDER
    name = raw_name.strip().lower()
    if name in OPENAI_ALIASES:
        name = "openai"
    elif name in OLLAMA_ALIASES:
        name = "ollama"
    default_model, default_url = provider_defaults(name)
    if name == "ollama":
        default_model = os.environ.get("STORYGRAM_OLLAMA_MODEL", default_model)
        default_url = os.environ.get("STORYGRAM_OLLAMA_URL", default_url)
    resolved_key = api_key if api_key is not None else os.environ.get("STORYGRAM_LLM_API_KEY")
    return ProviderConfig(
        provider=name,
        model=model or os.environ.get("STORYGRAM_LLM_MODEL") or default_model,
        base_url=base_url or os.environ.get("STORYGRAM_LLM_URL") or default_url,
        api_key=resolved_key or None,
    )


def _env_int(name: str, default: int) -> int:
    raw = os.environ.get(name)
    if raw is None or not raw.strip():
        return default
    try:
        value = int(raw)
    except ValueError:
        raise LLMAdapterError(f"{name} must be an integer") from None
    if value <= 0:
        raise LLMAdapterError(f"{name} must be positive")
    return value


def provider_from_config(config: ProviderConfig) -> Provider:
    """Build a provider instance from resolved settings."""
    if config.provider == "ollama":
        return OllamaProvider(
            model=config.model,
            base_url=config.base_url,
            timeout=_env_int("STORYGRAM_LLM_TIMEOUT", 120),
        )
    return OpenAICompatibleProvider(
        model=config.model,
        base_url=config.base_url,
        api_key=config.api_key,
        timeout=_env_int("STORYGRAM_LLM_TIMEOUT", 300),
        max_tokens=_env_int("STORYGRAM_LLM_MAX_TOKENS", 2048),
    )


def build_provider(
    provider: str,
    model: str | None = None,
    base_url: str | None = None,
    api_key: str | None = None,
) -> Provider:
    """Build a provider from a name and optional overrides."""
    return provider_from_config(provider_config(provider, model, base_url, api_key))


PROPOSAL_FIELDS = {
    "id",
    "type",
    "status",
    "title",
    "created_at",
    "updated_at",
    "target_ids",
    "evidence",
    "rationale",
    "confidence",
    "approval_state",
    "operations",
    "notes",
}


def canonical_ids(root: Path, limit: int = 300) -> list[str]:
    items, _ = validate_mod.load_records(Path(root))
    ids = [str(data["id"]) for _, data in items if isinstance(data.get("id"), str)]
    return sorted(ids)[:limit]


def build_prompt(source_text: str, known_ids: list[str] | None = None) -> str:
    ids = known_ids or []
    known = "\n".join(f"- {value}" for value in ids) if ids else "(none supplied)"
    example = (
        '{"id":"proposal:example","type":"Proposal","status":"proposed",'
        '"created_at":"2026-01-01T00:00:00+00:00","updated_at":"2026-01-01T00:00:00+00:00",'
        '"title":"Source capture","operations":['
        '{"op":"create","record_type":"Episode","record":{"id":"episode:source-capture",'
        '"type":"Episode","episode_type":"memory","status":"reported",'
        '"content":{"text":"<faithful source text>"},'
        '"created_at":"2026-01-01T00:00:00+00:00","updated_at":"2026-01-01T00:00:00+00:00"}},'
        '{"op":"create","record_type":"Person","record":{"id":"person:maria-bianchi",'
        '"type":"Person","name":"Maria Bianchi","status":"reported",'
        '"created_at":"2026-01-01T00:00:00+00:00","updated_at":"2026-01-01T00:00:00+00:00"},'
        '"evidence":["episode:source-capture"]}]}'
    )
    lines = [
        "You convert source material into a Storygram proposal for human review.",
        "Return one JSON object only. Do not use markdown fences, comments or explanations.",
        "",
        "Required structure:",
        '- The proposal id must start with "proposal:".',
        '- type must be "Proposal"; status must be "proposed".',
        "- operations must be a non-empty array.",
        "- The first operation MUST create exactly one Episode that captures the source.",
        '- Put the source text faithfully in that Episode record under "content": {"text": "..."}.',
        '- Use episode_type "memory", "interview", "letter", "document", "observation" or "other";',
        '  use status "reported" unless the source explicitly says otherwise.',
        "- Then add semantic operations only for facts explicitly stated",
        "  or directly implied by the source.",
        "- If the source is too short or has no clear facts, return only the Episode.",
        "- Do not invent people, places, dates, relationships, events or certainty.",
        "",
        "Semantic operations:",
        "- Allowed ops: create, update_metadata, supersede, archive.",
        "- Allowed record_type values: Episode, Assertion, Person, Organization,",
        "  Place, Period, Event, Source, MediaAsset, Annotation, Narrative,",
        "  Collection, Conflict.",
        "- Every non-Episode create MUST include evidence on the operation,",
        '  citing the new Episode id, for example "evidence": ["episode:source-capture"].',
        "- Put evidence on the operation, never inside the record object.",
        '- The record "type" must exactly equal the operation record_type.',
        "- Every record must include id, type, status, created_at, updated_at,",
        "  plus its type-specific required fields.",
        '- Record IDs use lowercase prefixes: "episode:...", "assertion:...", "person:...".',
        "- Use stable, descriptive IDs with hyphens; do not use spaces.",
        "- Use an existing ID when the known list contains the same entity.",
        "- Semantic operations must cite evidence IDs.",
        "  Evidence must be episode:, source: or annotation:.",
        "- NEVER create Relationship records: that schema has no endpoints yet.",
        "- Represent a relationship as an Assertion with predicate relation:sibling",
        "  (or another relation:* predicate), subject/object person IDs,",
        "  transaction_time.recorded_at and evidence on the operation.",
        "- An Assertion requires subject, predicate, status, transaction_time.recorded_at,",
        "  created_at and updated_at.",
        '- Every Assertion predicate MUST start with "relation:" (for example relation:sibling).',
        "- transaction_time.recorded_at is when the record is created; do not use the event date.",
        '- Put source dates in valid_time, for example {"start":"1990","precision":"year"}.',
        "- Do not create Period records; use Assertion.valid_time for periods.",
        "- Only reference IDs that are created in this proposal or listed under known IDs.",
        "- If you reference a new place, event or person, create that record first.",
        "- object must be a valid record ID from those prefixes.",
        "- For a literal fact such as an occupation, omit object and put the literal in value.",
        "- Never invent prefixes such as occupation: or event: for a predicate.",
        "- Do not add surnames or details that the source does not state.",
        "- Never invent an apply, approve or merged status.",
        "- Preserve uncertainty and conflicting evidence; never resolve a conflict silently.",
        "- If a real contradiction exists, create an explicit Conflict",
        "  operation with both assertion IDs.",
        "",
        "Complete example (format illustration only; do not copy its facts):",
        example,
        "",
        "Assertion example (format illustration only):",
        '{"op":"create","record_type":"Assertion","record":{'
        '"id":"assertion:maria-moved-to-torino","type":"Assertion",'
        '"subject":"person:maria-bianchi","predicate":"relation:moved_to",'
        '"object":"place:torino","status":"reported",'
        '"transaction_time":{"recorded_at":"2026-01-01T00:00:00+00:00"},'
        '"valid_time":{"start":"1990","precision":"year"},'
        '"created_at":"2026-01-01T00:00:00+00:00",'
        '"updated_at":"2026-01-01T00:00:00+00:00"},'
        '"evidence":["episode:source-capture"]}',
        "",
        "Literal-value assertion example (format illustration only):",
        '{"op":"create","record_type":"Assertion","record":{'
        '"id":"assertion:elena-worked-as-nurse","type":"Assertion",'
        '"subject":"person:elena","predicate":"relation:worked_as",'
        '"value":"nurse","status":"reported",'
        '"transaction_time":{"recorded_at":"2026-01-01T00:00:00+00:00"},'
        '"valid_time":{"start":"1985","precision":"year"},'
        '"created_at":"2026-01-01T00:00:00+00:00",'
        '"updated_at":"2026-01-01T00:00:00+00:00"},'
        '"evidence":["episode:source-capture"]}',
        "",
        "Known canonical IDs:",
        known,
        "",
        "Source material:",
        source_text,
        "",
    ]
    return "\n".join(lines)


def extract_json(text: str) -> dict[str, Any]:
    stripped = text.strip()
    stripped = re.sub(
        r"<think(?:ing)?>.*?</think(?:ing)?>", "", stripped, flags=re.DOTALL | re.IGNORECASE
    ).strip()
    fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", stripped, re.DOTALL)
    if fenced:
        stripped = fenced.group(1)
    try:
        data = json.loads(stripped)
    except json.JSONDecodeError:
        start = stripped.find("{")
        end = stripped.rfind("}")
        if start == -1 or end <= start:
            raise LLMAdapterError("Provider response did not contain a JSON object") from None
        try:
            data = json.loads(stripped[start : end + 1])
        except json.JSONDecodeError as exc:
            raise LLMAdapterError(f"Provider response is not valid JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise LLMAdapterError("Provider response must be a JSON object")
    return data


def normalize_proposal(
    data: dict[str, Any], now: str | None = None, proposal_id: str | None = None
) -> dict[str, Any]:
    timestamp = now or datetime.now(UTC).isoformat()
    raw_id = proposal_id or data.get("id")
    if not isinstance(raw_id, str) or not raw_id.strip():
        raw_id = f"proposal:llm-{uuid.uuid4().hex[:8]}"
    if not raw_id.startswith("proposal:"):
        raw_id = f"proposal:{raw_id}"
    operations = data.get("operations")
    if not isinstance(operations, list) or not operations:
        raise LLMAdapterError("Generated proposal has no operations")
    proposal = {key: data[key] for key in PROPOSAL_FIELDS if key in data}
    proposal.update(
        {
            "id": raw_id,
            "type": "Proposal",
            "status": "proposed",
            "created_at": timestamp,
            "updated_at": timestamp,
            "operations": operations,
        }
    )
    return proposal


class LLMAdapter:
    """Turn provider output into a validated in-memory proposal."""

    def __init__(
        self,
        provider: Provider,
        now: Callable[[], str] | None = None,
        id_factory: Callable[[], str] | None = None,
    ):
        self.provider = provider
        self._now = now or (lambda: datetime.now(UTC).isoformat())
        self._id_factory = id_factory or (lambda: f"proposal:llm-{uuid.uuid4().hex[:8]}")

    def generate(
        self, root: Path, source_text: str, known_ids: list[str] | None = None
    ) -> dict[str, Any]:
        if not source_text.strip():
            raise LLMAdapterError("Source text is empty")
        ids = canonical_ids(root) if known_ids is None else known_ids
        response = self.provider.complete(build_prompt(source_text, ids))
        proposal = normalize_proposal(
            extract_json(response), now=self._now(), proposal_id=self._id_factory()
        )
        errors = validate_mod.validate_instance(Path(root), proposal, TYPE_BY_NAME["Proposal"])
        if errors:
            raise LLMAdapterError("; ".join(errors))
        return proposal


def referenced_ids(proposal: dict[str, Any]) -> list[str]:
    return list(dict.fromkeys(iter_reference_strings(proposal)))


def save_pending(root: Path, proposal: dict[str, Any]) -> Path:
    """Persist a proposal under proposals/ only; canonical data is untouched."""
    root = Path(root)
    proposal_id = proposal.get("id")
    if not isinstance(proposal_id, str) or not proposal_id.startswith("proposal:"):
        raise LLMAdapterError("Proposal id must start with proposal:")
    errors = validate_mod.validate_instance(root, proposal, TYPE_BY_NAME["Proposal"])
    if errors:
        raise LLMAdapterError("; ".join(errors))
    if proposals_mod.find_proposal(root, proposal_id, include_applied=True):
        raise LLMAdapterError(f"Proposal already exists: {proposal_id}")
    destination = proposals_mod.pending_dir(root) / proposals_mod.safe_filename(proposal_id)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(proposal, indent=2) + "\n", encoding="utf-8")
    return destination
