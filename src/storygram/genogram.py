"""Experimental genogram generation."""

from __future__ import annotations

import json
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
        "supported": supported,
    }


def build_genogram(root: Path, person_id: str) -> dict[str, Any]:
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

    return {
        "person": person_id,
        "relations": sorted(relations, key=lambda item: str(item["record_id"])),
        "warnings": sorted(warnings),
    }
