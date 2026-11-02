"""Export functionality."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .registry import RECORD_TYPES


class ExportError(Exception):
    """Raised when canonical export input cannot be read safely."""


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
