"""Experimental genogram generation."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

FAMILY_PREDICATES = {
    "relation:parent",
    "relation:child",
    "relation:spouse",
    "relation:sibling",
    "relation:partner",
}


def build_genogram(root: Path, person_id: str) -> dict[str, Any]:
    relations = []
    warnings: set[str] = set()

    relationship_paths = sorted((root / "data" / "relationships").rglob("*.json"))
    if relationship_paths:
        warnings.add(
            "Relationship records have no endpoint metadata and were ignored; "
            "model family links as relation:* assertions"
        )

    for path in sorted((root / "data" / "assertions").rglob("*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if not isinstance(data, dict):
            continue
        predicate = str(data.get("predicate", ""))
        if not predicate.startswith("relation:"):
            continue
        if data.get("subject") == person_id:
            direction = "outgoing"
        elif data.get("object") == person_id:
            direction = "incoming"
        else:
            continue
        supported = predicate in FAMILY_PREDICATES
        if not supported:
            warnings.add(f"Unsupported relation predicate: {predicate}")
        relations.append(
            {
                "assertion_id": data.get("id"),
                "predicate": predicate,
                "subject": data.get("subject"),
                "object": data.get("object"),
                "direction": direction,
                "status": data.get("status"),
                "supported": supported,
            }
        )

    return {
        "person": person_id,
        "relations": sorted(relations, key=lambda item: str(item["assertion_id"])),
        "warnings": sorted(warnings),
    }
