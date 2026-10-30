"""Validation logic for canonical Storygram records."""

from __future__ import annotations

import json
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from .registry import RECORD_TYPES, TYPE_BY_NAME, RecordType, iter_reference_strings, schema_paths

try:
    from jsonschema import FormatChecker, ValidationError
    from jsonschema import validate as json_validate
except Exception:  # pragma: no cover - dependency is optional at runtime
    FormatChecker = None  # type: ignore[assignment,misc]
    json_validate = None  # type: ignore[assignment]
    ValidationError = Exception  # type: ignore[assignment,misc]


def load_schema(schema_path: Path) -> dict[str, Any] | None:
    """Load a JSON schema file, returning None when absent or malformed."""
    if not schema_path.exists():
        return None
    try:
        data = json.loads(schema_path.read_text(encoding="utf-8"))
    except Exception:
        return None
    return data if isinstance(data, dict) else None


def load_schema_for(root: Path, record_type: RecordType) -> dict[str, Any] | None:
    for candidate in schema_paths(root, record_type):
        schema = load_schema(Path(candidate))
        if schema is not None:
            return schema
    return None


def load_records(root: Path) -> tuple[list[tuple[Path, dict[str, Any]]], list[str]]:
    """Load every canonical JSON record under ``data/``.

    Returns record files paired with parsed data plus JSON parse errors.
    """
    root = Path(root)
    items: list[tuple[Path, dict[str, Any]]] = []
    errors: list[str] = []
    for record_type in RECORD_TYPES:
        base = root / "data" / record_type.directory
        if not base.exists():
            continue
        for path in sorted(base.rglob("*.json")):
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
            except Exception as exc:
                errors.append(f"{_label(root, path)}: invalid json: {exc}")
                continue
            if not isinstance(data, dict):
                errors.append(f"{_label(root, path)}: record must be a JSON object")
                continue
            items.append((path, data))
    return items, errors


def _label(root: Path, value: Path | str) -> str:
    path = Path(value)
    try:
        return str(path.relative_to(root))
    except ValueError:
        return str(path)


def _validate_instance(root: Path, data: dict[str, Any], record_type: RecordType) -> list[str]:
    schema = load_schema_for(root, record_type)
    if schema is None:
        return [f"missing schema {record_type.schema_file}"]
    if json_validate is None:
        if data.get("type") != record_type.name:
            return [f"type must be {record_type.name}"]
        return []
    try:
        checker = FormatChecker() if FormatChecker is not None else None
        json_validate(instance=data, schema=schema, format_checker=checker)
    except ValidationError as exc:
        return [f"schema validation error: {exc.message}"]
    return []


def validate_instance(root: Path, data: dict[str, Any], record_type: RecordType) -> list[str]:
    """Validate one in-memory record against its type schema."""
    return _validate_instance(root, data, record_type)


def validate_items(
    root: Path, items: Sequence[tuple[Path | str, dict[str, Any]]]
) -> dict[str, Any]:
    """Validate an in-memory set of records, including duplicate IDs and references."""
    root = Path(root)
    errors: list[str] = []
    ids: dict[str, str] = {}

    for path, data in items:
        label = _label(root, path)
        if not isinstance(data, dict):
            errors.append(f"{label}: record must be a JSON object")
            continue
        type_name = data.get("type")
        if not isinstance(type_name, str) or type_name not in TYPE_BY_NAME:
            errors.append(f"{label}: unknown or missing record type: {type_name!r}")
            continue
        record_type = TYPE_BY_NAME[type_name]
        record_id = data.get("id")
        if not isinstance(record_id, str) or not record_id:
            errors.append(f"{label}: missing or invalid id")
        else:
            if record_id in ids:
                errors.append(f"{label}: duplicate id {record_id} (also in {ids[record_id]})")
            else:
                ids[record_id] = label
        for message in _validate_instance(root, data, record_type):
            errors.append(f"{label}: {message}")

    for path, data in items:
        if not isinstance(data, dict):
            continue
        label = _label(root, path)
        for ref in iter_reference_strings(data):
            if ref not in ids:
                errors.append(f"{label}: missing reference {ref}")

    return {"ok": len(errors) == 0, "errors": errors, "warnings": []}


def validate_archive(root: Path) -> dict[str, Any]:
    """Validate all canonical records under an archive root."""
    items, load_errors = load_records(root)
    result = validate_items(root, items)
    result["errors"] = load_errors + result["errors"]
    result["ok"] = len(result["errors"]) == 0
    return result


def validate_referential_integrity(root: Path) -> dict[str, Any]:
    """Check duplicate IDs and unresolved references across canonical records."""
    items, load_errors = load_records(root)
    errors = list(load_errors)
    ids: dict[str, str] = {}
    for path, data in items:
        if not isinstance(data, dict):
            continue
        label = _label(root, path)
        record_id = data.get("id")
        if not isinstance(record_id, str) or not record_id:
            errors.append(f"{label}: missing or invalid id")
            continue
        if record_id in ids:
            errors.append(f"{label}: duplicate id {record_id} (also in {ids[record_id]})")
        else:
            ids[record_id] = label
    for path, data in items:
        if not isinstance(data, dict):
            continue
        label = _label(root, path)
        for ref in iter_reference_strings(data):
            if ref not in ids:
                errors.append(f"{label}: missing reference {ref}")
    return {"ok": len(errors) == 0, "errors": errors, "warnings": []}
