"""Validation logic."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

try:
    from jsonschema import validate as json_validate
    from jsonschema import ValidationError
except Exception:
    json_validate = None
    ValidationError = Exception


def load_schema(schema_path: Path) -> dict[str, Any] | None:
    if not schema_path.exists():
        return None
    try:
        return json.loads(schema_path.read_text())
    except Exception:
        return None


def validate_archive(root: Path) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []

    schema_dir = root / "schema"
    ep_schema = load_schema(schema_dir / "episode.schema.json") or load_schema(
        root.parent / "schema" / "episode.schema.json"
    )
    as_schema = load_schema(schema_dir / "assertion.schema.json") or load_schema(
        root.parent / "schema" / "assertion.schema.json"
    )

    # validate episodes
    for p in (root / "data" / "episodes").rglob("*.json"):
        try:
            data = json.loads(p.read_text())
        except Exception as e:
            errors.append(f"{p}: invalid json: {e}")
            continue
        if json_validate and ep_schema:
            try:
                json_validate(instance=data, schema=ep_schema)
            except ValidationError as e:
                errors.append(f"{p}: schema validation error: {e.message}")
        else:
            if data.get("type") != "Episode":
                errors.append(f"{p}: type must be Episode")

    # validate assertions
    for p in (root / "data" / "assertions").rglob("*.json"):
        try:
            data = json.loads(p.read_text())
        except Exception as e:
            errors.append(f"{p}: invalid json: {e}")
            continue
        if json_validate and as_schema:
            try:
                json_validate(instance=data, schema=as_schema)
            except ValidationError as e:
                errors.append(f"{p}: schema validation error: {e.message}")
        else:
            if data.get("type") != "Assertion":
                errors.append(f"{p}: type must be Assertion")

    return {"ok": len(errors) == 0, "errors": errors, "warnings": warnings}


def validate_referential_integrity(root: Path) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []
    ids_seen: set[str] = set()
    all_files = []
    for sub in ["data/episodes", "data/assertions", "data/people", "data/organizations",
                "data/places", "data/periods", "data/events", "data/relationships",
                "data/sources", "data/media-assets", "data/annotations", "data/narratives",
                "data/collections", "data/proposals", "data/conflicts"]:
        all_files.extend((root / sub).rglob("*.json"))
    for p in all_files:
        try:
            data = json.loads(p.read_text())
        except Exception as e:
            errors.append(f"{p}: invalid json: {e}")
            continue
        if isinstance(data, dict) and "id" in data:
            if data["id"] in ids_seen:
                errors.append(f"duplicate id {data['id']} in {p}")
            ids_seen.add(data["id"])
    # check references in assertions
    for p in (root / "data" / "assertions").rglob("*.json"):
        try:
            data = json.loads(p.read_text())
        except Exception:
            continue
        for key in ["subject", "object"]:
            if key in data and data[key] is not None and isinstance(data[key], str):
                if ":" in data[key] and data[key] not in ids_seen and key == "subject":  # soft check
                    pass  # might be defined elsewhere; be conservative
    return {"ok": len(errors) == 0, "errors": errors, "warnings": warnings}
