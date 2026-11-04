"""Safely turn exported records into a reviewable pending proposal."""

from __future__ import annotations

import copy
import json
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from . import validate
from .export import (
    ExportError,
    records_from_json,
    records_from_jsonld,
    records_from_markdown,
    records_from_yaml,
)
from .proposals import ProposalError, create_pending, plan_apply
from .registry import EVIDENCE_TYPE_NAMES, TYPE_BY_NAME

IMPORT_FORMATS = ("json", "jsonld", "yaml", "markdown")
FORMAT_BY_SUFFIX = {
    ".json": "json",
    ".jsonld": "jsonld",
    ".yaml": "yaml",
    ".yml": "yaml",
    ".md": "markdown",
    ".markdown": "markdown",
}


class ImportError(Exception):
    """Raised when an exported file cannot become a pending proposal."""


def detect_format(path: Path) -> str:
    """Infer the export format from a file suffix."""
    fmt = FORMAT_BY_SUFFIX.get(Path(path).suffix.lower())
    if fmt is None:
        raise ImportError(f"Cannot detect export format for {Path(path).name}; use --format")
    return fmt


def records_from_text(text: str, fmt: str) -> list[dict[str, Any]]:
    """Parse exported text in one of the supported formats."""
    try:
        if fmt == "json":
            return records_from_json(text)
        if fmt == "jsonld":
            return records_from_jsonld(json.loads(text))
        if fmt == "yaml":
            return records_from_yaml(text)
        if fmt == "markdown":
            return records_from_markdown(text)
    except (ExportError, json.JSONDecodeError) as exc:
        raise ImportError(f"Cannot parse {fmt} export: {exc}") from exc
    raise ImportError(f"Unsupported import format: {fmt}")


def read_records(path: Path, fmt: str | None = None) -> list[dict[str, Any]]:
    """Read and parse an export file, optionally forcing its format."""
    path = Path(path)
    resolved = fmt or detect_format(path)
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise ImportError(f"Cannot read {path}: {exc}") from exc
    records = records_from_text(text, resolved)
    if not records:
        raise ImportError(f"Export contains no records: {path}")
    return records


def _validate_records(root: Path, records: list[dict[str, Any]]) -> None:
    errors: list[str] = []
    seen: set[str] = set()
    for index, record in enumerate(records, start=1):
        label = f"record[{index}]"
        if not isinstance(record, dict):
            errors.append(f"{label}: record must be an object")
            continue
        record_id = record.get("id")
        if isinstance(record_id, str) and record_id:
            label = f"record[{index}] {record_id}"
        else:
            errors.append(f"{label}: missing or invalid id")
        if isinstance(record_id, str) and record_id:
            if record_id in seen:
                errors.append(f"{label}: duplicate id in export")
            seen.add(record_id)
        type_name = record.get("type")
        record_type = TYPE_BY_NAME.get(type_name) if isinstance(type_name, str) else None
        if record_type is None:
            errors.append(f"{label}: unknown or missing record type: {type_name!r}")
            continue
        if not record_type.proposable:
            errors.append(f"{label}: {record_type.name} records cannot be imported")
            continue
        errors.extend(
            f"{label}: {message}"
            for message in validate.validate_instance(root, record, record_type)
        )
    if errors:
        raise ImportError("; ".join(dict.fromkeys(errors)))


def _ordered_records(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Put evidence records first so they can support later operations."""
    evidence = [record for record in records if record.get("type") in EVIDENCE_TYPE_NAMES]
    others = [record for record in records if record.get("type") not in EVIDENCE_TYPE_NAMES]
    evidence.sort(key=lambda record: TYPE_BY_NAME[str(record["type"])].evidence_required)
    return evidence + others


def _operations(
    records: list[dict[str, Any]], canonical_evidence: list[str]
) -> list[dict[str, Any]]:
    available = list(dict.fromkeys(canonical_evidence))
    operations: list[dict[str, Any]] = []
    for record in _ordered_records(records):
        record_type = TYPE_BY_NAME[str(record["type"])]
        operation: dict[str, Any] = {
            "op": "create",
            "record_type": record_type.name,
            "record": copy.deepcopy(record),
        }
        if record_type.evidence_required and available:
            operation["evidence"] = list(available)
        operations.append(operation)
        if record_type.name in EVIDENCE_TYPE_NAMES:
            record_id = str(record["id"])
            if record_id not in available:
                available.append(record_id)
    return operations


def _default_proposal_id(path: Path) -> str:
    slug = re.sub(r"[^A-Za-z0-9._~-]+", "-", Path(path).stem).strip("-")
    return f"proposal:import-{slug or 'records'}"


def build_proposal(
    records: list[dict[str, Any]],
    proposal_id: str,
    *,
    title: str | None = None,
    evidence: list[str] | None = None,
    now: str | None = None,
) -> dict[str, Any]:
    """Build a create-only proposal envelope from imported records."""
    if not proposal_id.startswith("proposal:"):
        raise ImportError("proposal id must start with proposal:")
    timestamp = now or datetime.now(UTC).isoformat()
    return {
        "id": proposal_id,
        "type": "Proposal",
        "status": "proposed",
        "title": title or f"Import {len(records)} record(s)",
        "created_at": timestamp,
        "updated_at": timestamp,
        "operations": _operations(records, list(evidence or [])),
    }


def import_records(
    root: Path,
    path: Path,
    *,
    fmt: str | None = None,
    proposal_id: str | None = None,
    title: str | None = None,
    evidence: list[str] | None = None,
    now: str | None = None,
) -> dict[str, Any]:
    """Import an export into ``proposals/`` after full proposal validation.

    Canonical data is never written here. The resulting pending proposal must
    still be reviewed and approved by a human through the normal CLI or UI.
    """
    root = Path(root)
    path = Path(path)
    records = read_records(path, fmt)
    _validate_records(root, records)
    resolved_id = proposal_id or _default_proposal_id(path)
    proposal = build_proposal(records, resolved_id, title=title, evidence=evidence, now=now)
    try:
        plan = plan_apply(root, proposal, now=now)
        destination = create_pending(root, proposal)
    except ProposalError as exc:
        raise ImportError("; ".join(exc.errors)) from exc
    return {
        "ok": True,
        "proposal_id": resolved_id,
        "path": str(destination),
        "records": len(records),
        "operations": plan.preview,
    }
