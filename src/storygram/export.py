"""Export and round-trip parsing for canonical Storygram records."""

from __future__ import annotations

import copy
import json
import re
from pathlib import Path
from typing import Any

import yaml

from .registry import RECORD_TYPES


class ExportError(Exception):
    """Raised when canonical export input cannot be read or parsed safely."""


_MARKDOWN_RECORD_START = "<!-- storygram:record -->"
_MARKDOWN_RECORD_END = "<!-- /storygram:record -->"
_MARKDOWN_RECORD = re.compile(
    re.escape(_MARKDOWN_RECORD_START)
    + r"\n---\n(.*?)\n---\n\n(.*?)\n"
    + re.escape(_MARKDOWN_RECORD_END),
    re.DOTALL,
)


def _iter_records(root: Path):
    for record_type in RECORD_TYPES:
        if record_type.name == "Proposal":
            continue
        directory = root / "data" / record_type.directory
        for path in sorted(directory.rglob("*.json")):
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as exc:
                raise ExportError(f"Cannot read {path}: {exc}") from exc
            if not isinstance(data, dict):
                raise ExportError(f"Expected a JSON object in {path}")
            yield data


def export_json(root: Path, visibility_filter: set[str] | None = None) -> list[dict[str, Any]]:
    results = []
    for data in _iter_records(root):
        if visibility_filter is not None and data.get("visibility") not in visibility_filter:
            continue
        results.append(data)
    return sorted(results, key=lambda record: str(record.get("id", "")))


def export_jsonld(root: Path, visibility_filter: set[str] | None = None) -> dict[str, Any]:
    graph = []
    for item in export_json(root, visibility_filter):
        node = {key: value for key, value in item.items() if key not in {"id", "type"}}
        graph.append({"@id": item.get("id"), "@type": item.get("type"), **node})
    return {
        "@context": {"@vocab": "https://storygram.local/vocab#"},
        "@graph": graph,
    }


def records_from_jsonld(payload: Any) -> list[dict[str, Any]]:
    """Rebuild canonical records from an exported JSON-LD graph."""
    if not isinstance(payload, dict):
        raise ExportError("JSON-LD input must be an object")
    graph = payload.get("@graph")
    if not isinstance(graph, list):
        raise ExportError("JSON-LD input must contain an @graph list")
    records = []
    for node in graph:
        if not isinstance(node, dict):
            raise ExportError("Each JSON-LD graph node must be an object")
        record = copy.deepcopy(node)
        record_id = record.pop("@id", None)
        record_type = record.pop("@type", None)
        if not isinstance(record_id, str) or not record_id:
            raise ExportError("Each JSON-LD graph node needs an @id")
        if not isinstance(record_type, str) or not record_type:
            raise ExportError(f"JSON-LD node {record_id} needs an @type")
        records.append({"id": record_id, "type": record_type, **record})
    return sorted(records, key=lambda item: str(item.get("id", "")))


def export_yaml(root: Path, visibility_filter: set[str] | None = None) -> str:
    """Export canonical records as a YAML sequence that can be parsed back."""
    return yaml.safe_dump(
        export_json(root, visibility_filter),
        sort_keys=False,
        allow_unicode=True,
        default_flow_style=False,
    )


def records_from_yaml(text: str) -> list[dict[str, Any]]:
    """Rebuild canonical records from the YAML export representation."""
    try:
        payload = yaml.safe_load(text)
    except yaml.YAMLError as exc:
        raise ExportError(f"Cannot parse YAML export: {exc}") from exc
    if payload is None:
        return []
    if isinstance(payload, dict) and "records" in payload:
        payload = payload["records"]
    if isinstance(payload, dict):
        payload = [payload]
    if not isinstance(payload, list):
        raise ExportError("YAML export must contain a record or a list of records")
    records = []
    for item in payload:
        if not isinstance(item, dict):
            raise ExportError("Each YAML record must be an object")
        records.append(item)
    return sorted(records, key=lambda item: str(item.get("id", "")))


def _markdown_record(record: dict[str, Any]) -> str:
    front = copy.deepcopy(record)
    body = ""
    body_field: str | None = None
    if front.get("type") == "Episode":
        content = front.get("content")
        if isinstance(content, dict) and isinstance(content.get("text"), str):
            body = content["text"]
            body_field = "content.text"
            remaining = {key: value for key, value in content.items() if key != "text"}
            if remaining:
                front["content"] = remaining
            else:
                front.pop("content")
    elif isinstance(front.get("notes"), str):
        body = front.pop("notes")
        body_field = "notes"
    front["storygram_body"] = body_field
    front_text = yaml.safe_dump(
        front,
        sort_keys=False,
        allow_unicode=True,
        default_flow_style=False,
    )
    return f"{_MARKDOWN_RECORD_START}\n---\n{front_text}---\n\n{body}\n{_MARKDOWN_RECORD_END}\n"


def export_markdown(root: Path, visibility_filter: set[str] | None = None) -> str:
    """Export records as Markdown blocks with reversible YAML front matter.

    Long text lives in the rendered body (Episode ``content.text`` or ``notes``);
    the front matter remains the source of truth for parsing back.
    """
    return "\n".join(_markdown_record(record) for record in export_json(root, visibility_filter))


def records_from_markdown(text: str) -> list[dict[str, Any]]:
    """Rebuild canonical records from Markdown export blocks."""
    if not text.strip():
        return []
    matches = list(_MARKDOWN_RECORD.finditer(text))
    if not matches:
        raise ExportError("Markdown record is missing YAML front matter or end marker")
    if _MARKDOWN_RECORD.sub("", text).strip():
        raise ExportError("Markdown contains data outside storygram record blocks")
    records = []
    for match in matches:
        try:
            front = yaml.safe_load(match.group(1))
        except yaml.YAMLError as exc:
            raise ExportError(f"Cannot parse Markdown front matter: {exc}") from exc
        if not isinstance(front, dict):
            raise ExportError("Markdown front matter must be an object")
        body = match.group(2)
        body_field = front.pop("storygram_body", None)
        if body_field == "content.text":
            content = front.get("content")
            if content is None:
                content = {}
            if not isinstance(content, dict):
                raise ExportError("Episode content must be an object")
            content["text"] = body
            front["content"] = content
        elif body_field == "notes":
            front["notes"] = body
        elif body_field is not None:
            raise ExportError(f"Unsupported storygram_body field: {body_field!r}")
        elif body:
            raise ExportError("Markdown body is present without a storygram_body marker")
        records.append(front)
    return sorted(records, key=lambda item: str(item.get("id", "")))
