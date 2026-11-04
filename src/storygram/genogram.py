"""Experimental genogram generation."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

CLOSED_STATUSES = {"superseded", "archived", "rejected"}
FAMILY_PREDICATES = {
    "relation:parent",
    "relation:child",
    "relation:spouse",
    "relation:sibling",
    "relation:partner",
}


def _load(path: Path) -> dict[str, Any] | None:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return data if isinstance(data, dict) else None


def _relation(
    data: dict[str, Any],
    person_id: str,
    record_type: str,
    id_key: str,
    warnings: set[str],
) -> dict[str, Any] | None:
    if data.get("status") in CLOSED_STATUSES:
        return None
    predicate = data.get("predicate")
    subject = data.get("subject")
    obj = data.get("object")
    if not isinstance(predicate, str) or not isinstance(subject, str) or not isinstance(obj, str):
        return None
    if subject == person_id:
        direction = "outgoing"
    elif obj == person_id:
        direction = "incoming"
    else:
        return None
    supported = predicate in FAMILY_PREDICATES
    if not supported:
        warnings.add(f"Unsupported relation predicate: {predicate}")
    return {
        "record_id": data.get("id"),
        "record_type": record_type,
        id_key: data.get("id"),
        "predicate": predicate,
        "subject": subject,
        "object": obj,
        "direction": direction,
        "status": data.get("status"),
        "valid_time": data.get("valid_time"),
        "transaction_time": data.get("transaction_time"),
        "supported": supported,
    }


def _recorded_at(entry: dict[str, Any]) -> datetime | None:
    transaction_time = entry.get("transaction_time")
    if not isinstance(transaction_time, dict):
        return None
    recorded_at = transaction_time.get("recorded_at")
    if not isinstance(recorded_at, str):
        return None
    try:
        value = datetime.fromisoformat(recorded_at.replace("Z", "+00:00"))
    except ValueError:
        return None
    return value if value.tzinfo is not None else value.replace(tzinfo=UTC)


def _representative_key(entry: dict[str, Any]) -> tuple[int, int, float, str]:
    recorded_at = _recorded_at(entry)
    if recorded_at is None:
        timestamp = 0.0
    else:
        try:
            timestamp = -recorded_at.timestamp()
        except (OSError, OverflowError, ValueError):
            timestamp = 0.0
    return (
        0 if entry["record_type"] == "Relationship" else 1,
        0 if recorded_at is not None else 1,
        timestamp,
        str(entry["record_id"]),
    )


def _canonical_interval(value: dict[str, Any]) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _interval_sort_key(field: str, value: dict[str, Any]) -> tuple[str, str, str]:
    if field == "valid_time":
        return (
            str(value.get("start") or ""),
            str(value.get("end") or ""),
            _canonical_interval(value),
        )
    return (
        str(value.get("recorded_at") or ""),
        str(value.get("recorded_until") or ""),
        _canonical_interval(value),
    )


def _unique_intervals(entries: list[dict[str, Any]], field: str) -> list[dict[str, Any]]:
    unique: dict[str, dict[str, Any]] = {}
    for entry in entries:
        value = entry.get(field)
        if isinstance(value, dict):
            unique.setdefault(_canonical_interval(value), value)
    return sorted(unique.values(), key=lambda value: _interval_sort_key(field, value))


def _deduplicate(relations: list[dict[str, Any]]) -> list[dict[str, Any]]:
    groups: dict[tuple[str, str, str], list[dict[str, Any]]] = {}
    for entry in relations:
        key = (entry["subject"], entry["predicate"], entry["object"])
        groups.setdefault(key, []).append(entry)

    merged = []
    for entries in groups.values():
        representative = dict(sorted(entries, key=_representative_key)[0])
        representative["valid_times"] = _unique_intervals(entries, "valid_time")
        representative["transaction_times"] = _unique_intervals(entries, "transaction_time")
        representative["related_ids"] = sorted(
            {str(entry["record_id"]) for entry in entries if entry.get("record_id") is not None}
        )
        merged.append(representative)
    return merged


def _year_value(value: Any) -> int | None:
    if not isinstance(value, str) or len(value) < 4:
        return None
    prefix = value[:4]
    if not prefix.isdigit():
        return None
    try:
        return int(prefix)
    except ValueError:
        return None


def _intervals_overlap_at(valid_times: list[dict[str, Any]], at_year: int) -> bool:
    if not valid_times:
        return True
    for value in valid_times:
        if not isinstance(value, dict):
            continue
        start = _year_value(value.get("start"))
        end = _year_value(value.get("end"))
        if (start is None or start <= at_year) and (end is None or end >= at_year):
            return True
    return False


def build_genogram(root: Path, person_id: str, at: str | None = None) -> dict[str, Any]:
    relations = []
    warnings: set[str] = set()

    for path in sorted((root / "data" / "relationships").rglob("*.json")):
        data = _load(path)
        if data is None or data.get("status") in CLOSED_STATUSES:
            continue
        endpoints = (data.get("subject"), data.get("predicate"), data.get("object"))
        if not all(isinstance(value, str) for value in endpoints):
            warnings.add(f"Relationship without complete endpoints was ignored: {data.get('id')}")
            continue
        entry = _relation(data, person_id, "Relationship", "relationship_id", warnings)
        if entry is not None:
            relations.append(entry)

    for path in sorted((root / "data" / "assertions").rglob("*.json")):
        data = _load(path)
        if data is None:
            continue
        predicate = str(data.get("predicate", ""))
        if not predicate.startswith("relation:"):
            continue
        entry = _relation(data, person_id, "Assertion", "assertion_id", warnings)
        if entry is not None:
            relations.append(entry)

    merged = _deduplicate(relations)
    at_year = _year_value(at) if at else None
    if at_year is not None:
        merged = [
            relation
            for relation in merged
            if _intervals_overlap_at(relation.get("valid_times") or [], at_year)
        ]
    return {
        "person": person_id,
        "at": at,
        "relations": sorted(merged, key=lambda item: str(item["record_id"])),
        "warnings": sorted(warnings),
    }
