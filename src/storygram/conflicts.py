"""Conflict listing."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def _load_json(path: Path) -> dict[str, Any] | None:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return data if isinstance(data, dict) else None


def _pair_key(assertions: list[str]) -> tuple[str, ...]:
    return tuple(sorted(set(assertions)))


def _evidence(records: list[dict[str, Any]]) -> list[str]:
    values: set[str] = set()
    for record in records:
        for field in ("produced_by", "supported_by"):
            values.update(str(item) for item in record.get(field) or [])
    return sorted(values)


def list_conflicts(root: Path, status: str | None = None) -> list[dict[str, Any]]:
    assertions: dict[str, dict[str, Any]] = {}
    for path in sorted((root / "data" / "assertions").rglob("*.json")):
        data = _load_json(path)
        if data is not None and isinstance(data.get("id"), str):
            assertions[data["id"]] = data

    results: list[dict[str, Any]] = []
    explicit_pairs: set[tuple[str, ...]] = set()
    for path in sorted((root / "data" / "conflicts").rglob("*.json")):
        data = _load_json(path)
        if data is None:
            continue
        explicit_pairs.add(_pair_key([str(item) for item in data.get("assertions") or []]))
        results.append(data)

    seen_pairs = set(explicit_pairs)
    for assertion_id in sorted(assertions):
        data = assertions[assertion_id]
        contradicts = [str(item) for item in data.get("contradicts") or []]
        if not contradicts:
            continue
        pair = _pair_key([assertion_id, *contradicts])
        if pair in seen_pairs:
            continue
        seen_pairs.add(pair)
        records = [assertions[item] for item in pair if item in assertions]
        results.append(
            {
                "id": "derived:" + "+".join(pair),
                "type": "DerivedConflict",
                "assertions": list(pair),
                "status": "open",
                "relation": "contradicts",
                "derived": True,
                "assertion_records": records,
                "evidence": _evidence(records),
            }
        )

    if status:
        results = [conflict for conflict in results if conflict.get("status") == status]
    return sorted(results, key=lambda conflict: str(conflict.get("id", "")))
