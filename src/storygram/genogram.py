"""Genogram generation."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def build_genogram(root: Path, person_id: str) -> dict[str, Any]:
    relations = []
    for p in (root / "data" / "relationships").rglob("*.json"):
        try:
            data = json.loads(p.read_text())
            relations.append(data)
        except Exception:
            continue
    for p in (root / "data" / "assertions").rglob("*.json"):
        try:
            data = json.loads(p.read_text())
            if data.get("predicate", "").startswith("relation:") and data.get("subject") == person_id:
                relations.append({"id": data.get("id"), "type": "AssertionRelation", "data": data})
        except Exception:
            continue
    return {"person": person_id, "relations": relations}
