"""Timeline generation."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

CLOSED_STATUSES = {"superseded", "archived", "rejected"}


def _valid_start(record: dict[str, Any]) -> str:
    valid_time = record.get("valid_time") or {}
    start = valid_time.get("start")
    return str(start) if start is not None else "~"


def build_timeline(root: Path, entity_id: str) -> list[dict[str, Any]]:
    timeline = []
    for path in sorted((root / "data" / "assertions").rglob("*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if not isinstance(data, dict):
            continue
        if data.get("status") in CLOSED_STATUSES:
            continue
        if data.get("subject") != entity_id and data.get("object") != entity_id:
            continue
        timeline.append(
            {
                "assertion_id": data.get("id"),
                "subject": data.get("subject"),
                "predicate": data.get("predicate"),
                "object": data.get("object"),
                "valid_time": data.get("valid_time"),
                "transaction_time": data.get("transaction_time"),
                "status": data.get("status"),
                "certainty": data.get("certainty"),
                "confidence": data.get("confidence"),
                "produced_by": data.get("produced_by") or [],
                "supported_by": data.get("supported_by") or [],
            }
        )
    return sorted(timeline, key=lambda item: (_valid_start(item), str(item["assertion_id"])))
