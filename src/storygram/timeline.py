"""Timeline generation."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

CLOSED_STATUSES = {"superseded", "archived", "rejected"}
COLLECTION_PREFIX = "collection:"
MEMBERSHIP_PREDICATE = "relation:member_of"


def _valid_start(record: dict[str, Any]) -> str:
    valid_time = record.get("valid_time") or {}
    start = valid_time.get("start")
    return str(start) if start is not None else "~"


def _open_assertions(root: Path) -> list[dict[str, Any]]:
    assertions = []
    for path in sorted((root / "data" / "assertions").rglob("*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if not isinstance(data, dict):
            continue
        if data.get("status") in CLOSED_STATUSES:
            continue
        assertions.append(data)
    return assertions


def _collection_members(assertions: list[dict[str, Any]], collection_id: str) -> set[str]:
    members = {collection_id}
    for data in assertions:
        if data.get("predicate") != MEMBERSHIP_PREDICATE:
            continue
        if data.get("object") != collection_id:
            continue
        subject = data.get("subject")
        if isinstance(subject, str):
            members.add(subject)
    return members


def _entry(data: dict[str, Any]) -> dict[str, Any]:
    return {
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


def build_timeline(root: Path, record_id: str | None = None) -> list[dict[str, Any]]:
    """Build an entity, place, collection or archive timeline.

    A collection timeline includes assertions about the collection itself and
    about records that assert ``relation:member_of`` the collection. Passing
    ``None`` builds an archive-level timeline over every open assertion.
    """
    assertions = _open_assertions(root)
    if record_id is None:
        selected = assertions
    else:
        if record_id.startswith(COLLECTION_PREFIX):
            related_ids = _collection_members(assertions, record_id)
        else:
            related_ids = {record_id}
        selected = [
            data
            for data in assertions
            if data.get("subject") in related_ids or data.get("object") in related_ids
        ]
    timeline = [_entry(data) for data in selected]
    return sorted(timeline, key=lambda item: (_valid_start(item), str(item["assertion_id"])))
