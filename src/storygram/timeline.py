"""Timeline generation."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def build_timeline(root: Path, entity_id: str) -> list[dict[str, Any]]:
    timeline = []
    for p in (root / "data" / "assertions").rglob("*.json"):
        try:
            data = json.loads(p.read_text())
        except Exception:
            continue
        if data.get("subject") == entity_id or data.get("object") == entity_id:
            timeline.append({
                "assertion_id": data.get("id"),
                "subject": data.get("subject"),
                "predicate": data.get("predicate"),
                "object": data.get("object"),
                "valid_time": data.get("valid_time"),
                "status": data.get("status"),
            })
    return timeline
