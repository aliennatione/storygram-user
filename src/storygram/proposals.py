"""Proposal validation and atomic application engine."""

from __future__ import annotations

import copy
import json
import os
import re
import subprocess
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from . import validate
from .registry import (
    EVIDENCE_TYPE_NAMES,
    TYPE_BY_NAME,
    RecordType,
    type_for_id,
)

SEMANTIC_OPS = {"create", "supersede", "archive"}
CLOSED_STATUSES = {"archived", "rejected", "superseded"}


class ProposalError(Exception):
    """Raised when a proposal cannot be planned or applied."""

    def __init__(self, errors: list[str]):
        self.errors = errors
        super().__init__("; ".join(errors))


class ProposalNotFoundError(ProposalError):
    """Raised when a requested proposal does not exist."""


class ProposalConflictError(ProposalError):
    """Raised when a proposal state forbids the requested change."""


@dataclass
class ApplyPlan:
    proposal: dict[str, Any]
    proposal_path: Path
    writes: dict[Path, dict[str, Any]] = field(default_factory=dict)
    archived_path: Path | None = None
    archived_proposal: dict[str, Any] | None = None
    preview: list[dict[str, Any]] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def _now(value: str | None = None) -> str:
    return value or datetime.now(UTC).isoformat()


def pending_dir(root: Path) -> Path:
    return Path(root) / "proposals"


def applied_dir(root: Path) -> Path:
    return Path(root) / "data" / "proposals"


def safe_filename(record_id: str) -> str:
    safe = re.sub(r"[^A-Za-z0-9._~-]+", "_", record_id.replace(":", "_"))
    return f"{safe}.json"


def _load_json(path: Path) -> dict[str, Any] | None:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None
    return data if isinstance(data, dict) else None


def _find_in(directory: Path, proposal_id: str) -> Path | None:
    if not directory.exists():
        return None
    for path in sorted(directory.glob("*.json")):
        data = _load_json(path)
        if data and data.get("id") == proposal_id:
            return path
    return None


def find_proposal(root: Path, proposal_id: str, include_applied: bool = False) -> Path | None:
    found = _find_in(pending_dir(root), proposal_id)
    if found is None and include_applied:
        return find_applied_proposal(root, proposal_id)
    return found


def find_applied_proposal(root: Path, proposal_id: str) -> Path | None:
    return _find_in(applied_dir(root), proposal_id)


def list_proposals(root: Path, include_applied: bool = False) -> list[tuple[Path, dict[str, Any]]]:
    dirs = [pending_dir(root)]
    if include_applied:
        dirs.append(applied_dir(root))
    results: list[tuple[Path, dict[str, Any]]] = []
    for directory in dirs:
        if not directory.exists():
            continue
        for path in sorted(directory.glob("*.json")):
            data = _load_json(path)
            if data is not None:
                results.append((path, data))
    return results


def _write_json_atomic(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp-{os.getpid()}")
    temporary.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def _pending_id(proposal: Any) -> str:
    if not isinstance(proposal, dict):
        raise ProposalError(["proposal must be a JSON object"])
    proposal_id = proposal.get("id")
    if not isinstance(proposal_id, str) or not proposal_id.startswith("proposal:"):
        raise ProposalError(["proposal id must start with proposal:"])
    return proposal_id


def _validate_pending(root: Path, proposal: dict[str, Any]) -> None:
    errors = validate.validate_instance(root, proposal, TYPE_BY_NAME["Proposal"])
    if errors:
        raise ProposalError(errors)
    if proposal.get("status") in {"merged", "rejected", "archived"}:
        raise ProposalConflictError(
            [f"proposal status {proposal.get('status')} cannot be used for a pending proposal"]
        )


def create_pending(root: Path, proposal: dict[str, Any]) -> Path:
    """Create a new pending proposal without touching canonical data."""
    root = Path(root)
    proposal_id = _pending_id(proposal)
    if find_proposal(root, proposal_id, include_applied=True) is not None:
        raise ProposalConflictError([f"proposal already exists: {proposal_id}"])
    data = copy.deepcopy(proposal)
    _validate_pending(root, data)
    destination = pending_dir(root) / safe_filename(proposal_id)
    _write_json_atomic(destination, data)
    return destination


def update_pending(
    root: Path, proposal_id: str, proposal: dict[str, Any], now: str | None = None
) -> Path:
    """Replace the contents of an existing pending proposal."""
    root = Path(root)
    if find_applied_proposal(root, proposal_id) is not None:
        raise ProposalConflictError([f"proposal is already applied: {proposal_id}"])
    path = find_proposal(root, proposal_id)
    if path is None:
        raise ProposalNotFoundError([f"pending proposal not found: {proposal_id}"])
    original = _load_json(path)
    if original is None:
        raise ProposalError([f"cannot read proposal: {_record_label(root, path)}"])
    if original.get("status") in {"merged", "rejected", "archived"}:
        raise ProposalConflictError(
            [f"proposal is already {original.get('status')}: {proposal_id}"]
        )
    if not isinstance(proposal, dict):
        raise ProposalError(["proposal must be a JSON object"])
    if proposal.get("id") != proposal_id:
        raise ProposalError(["proposal id cannot change while editing"])
    data = copy.deepcopy(proposal)
    data["created_at"] = original.get("created_at", data.get("created_at"))
    data["updated_at"] = _now(now)
    _validate_pending(root, data)
    _write_json_atomic(path, data)
    return path


def _record_label(root: Path, path: Path) -> str:
    try:
        return str(path.relative_to(root))
    except ValueError:
        return str(path)


def _load_working(root: Path) -> tuple[dict[str, dict[str, Any]], dict[str, Path], list[str]]:
    items, errors = validate.load_records(root)
    records: dict[str, dict[str, Any]] = {}
    paths: dict[str, Path] = {}
    for path, data in items:
        record_id = data.get("id")
        if not isinstance(record_id, str) or not record_id:
            errors.append(f"{_record_label(root, path)}: missing or invalid id")
            continue
        if record_id in records:
            errors.append(f"{_record_label(root, path)}: duplicate id {record_id}")
            continue
        records[record_id] = copy.deepcopy(data)
        paths[record_id] = path
    return records, paths, errors


def _evidence_ids(proposal: dict[str, Any], operation: dict[str, Any]) -> list[str]:
    values: list[str] = []
    for source in (proposal.get("evidence"), operation.get("evidence")):
        if isinstance(source, list):
            values.extend(str(item) for item in source)
    return list(dict.fromkeys(values))


def _validate_evidence(
    evidence: list[str],
    records: dict[str, dict[str, Any]],
    record_type: RecordType,
    operation_label: str,
    errors: list[str],
) -> None:
    if record_type.evidence_required and not evidence:
        errors.append(f"{operation_label}: evidence is required")
    for ref in evidence:
        if ref not in records:
            errors.append(f"{operation_label}: evidence not found in canonical data: {ref}")
            continue
        ref_type = type_for_id(ref)
        if ref_type is None or ref_type.name not in EVIDENCE_TYPE_NAMES:
            errors.append(
                f"{operation_label}: evidence must be Episode, Source or Annotation: {ref}"
            )


def _record_errors(
    root: Path, record: dict[str, Any], record_type: RecordType, label: str
) -> list[str]:
    return [
        f"{label}: {message}" for message in validate.validate_instance(root, record, record_type)
    ]


def _new_record_path(root: Path, record: dict[str, Any]) -> Path:
    record_type = TYPE_BY_NAME[str(record["type"])]
    return Path(root) / "data" / record_type.directory / safe_filename(str(record["id"]))


def _validate_record_identity(
    record: Any, record_type: RecordType, label: str, errors: list[str]
) -> str | None:
    if not isinstance(record, dict):
        errors.append(f"{label}: record must be an object")
        return None
    record_id = record.get("id")
    if not isinstance(record_id, str) or not record_id.startswith(f"{record_type.id_prefix}:"):
        errors.append(f"{label}: record id must start with {record_type.id_prefix}:")
        return None
    if record.get("type") != record_type.name:
        errors.append(f"{label}: record type must be {record_type.name}")
    return record_id


def _target_id(operation: dict[str, Any], label: str, errors: list[str]) -> str | None:
    target_id = operation.get("target_id")
    if not isinstance(target_id, str) or not target_id:
        errors.append(f"{label}: target_id is required")
        return None
    return target_id


def _check_target(
    target_id: str | None,
    records: dict[str, dict[str, Any]],
    record_type: RecordType,
    label: str,
    errors: list[str],
) -> str | None:
    if target_id is None:
        return None
    target = records.get(target_id)
    if target is None:
        errors.append(f"{label}: target not found in canonical data: {target_id}")
        return None
    if target.get("type") != record_type.name:
        errors.append(f"{label}: target {target_id} is not a {record_type.name}")
        return None
    return target_id


def _year(value: Any) -> int | None:
    if not isinstance(value, str):
        return None
    match = re.search(r"(\d{4})", value)
    return int(match.group(1)) if match else None


def _valid_time_overlap(left: Any, right: Any) -> bool:
    if not isinstance(left, dict) or not isinstance(right, dict):
        return True
    if left.get("precision") in {"unknown", "approximate"} or right.get("precision") in {
        "unknown",
        "approximate",
    }:
        return True
    left_start = _year(left.get("start"))
    right_start = _year(right.get("start"))
    if left_start is None or right_start is None:
        return True
    left_end = _year(left.get("end"))
    right_end = _year(right.get("end"))
    left_end = 10**9 if left_end is None else left_end
    right_end = 10**9 if right_end is None else right_end
    return left_start <= right_end and right_start <= left_end


def _assertions_conflict(left: dict[str, Any], right: dict[str, Any]) -> bool:
    if left.get("id") == right.get("id"):
        return False
    if left.get("status") in CLOSED_STATUSES or right.get("status") in CLOSED_STATUSES:
        return False
    if left.get("subject") != right.get("subject"):
        return False
    if left.get("predicate") != right.get("predicate"):
        return False
    if left.get("object") == right.get("object") and left.get("value") == right.get("value"):
        return False
    return _valid_time_overlap(left.get("valid_time"), right.get("valid_time"))


def _conflict_modeled(records: dict[str, dict[str, Any]], left_id: str, right_id: str) -> bool:
    for record in records.values():
        if record.get("type") != "Conflict":
            continue
        if record.get("status") in {"rejected"}:
            continue
        assertions = record.get("assertions")
        if isinstance(assertions, list) and left_id in assertions and right_id in assertions:
            return True
    return False


def _detect_conflicts(
    records: dict[str, dict[str, Any]], touched_assertions: set[str], errors: list[str]
) -> None:
    assertions = [record for record in records.values() if record.get("type") == "Assertion"]
    for record_id in sorted(touched_assertions):
        proposed = records.get(record_id)
        if not isinstance(proposed, dict):
            continue
        if proposed.get("status") in CLOSED_STATUSES:
            continue
        superseded = set(proposed.get("supersedes") or [])
        for other in assertions:
            other_id = other.get("id")
            if not isinstance(other_id, str) or other_id in superseded:
                continue
            if _assertions_conflict(proposed, other) and not _conflict_modeled(
                records, record_id, other_id
            ):
                errors.append(
                    "unmodelled conflict: "
                    f"{record_id} contradicts {other_id}; add an explicit Conflict operation"
                )


def plan_apply(root: Path, proposal: dict[str, Any], now: str | None = None) -> ApplyPlan:
    root = Path(root)
    timestamp = _now(now)
    errors: list[str] = []
    proposal_type = TYPE_BY_NAME["Proposal"]
    errors.extend(
        f"proposal: {message}"
        for message in validate.validate_instance(root, proposal, proposal_type)
    )
    if proposal.get("status") in {"rejected", "merged", "archived"}:
        errors.append(f"proposal: status {proposal.get('status')} cannot be applied")
    operations = proposal.get("operations")
    if not isinstance(operations, list) or not operations:
        errors.append("proposal: operations must be a non-empty array")
        operations = []

    records, paths, load_errors = _load_working(root)
    errors.extend(load_errors)
    original = copy.deepcopy(records)
    touched_assertions: set[str] = set()
    preview: list[dict[str, Any]] = []

    for index, operation in enumerate(operations):
        label = f"operation[{index}]"
        if not isinstance(operation, dict):
            errors.append(f"{label}: must be an object")
            continue
        op = operation.get("op")
        if op not in {"create", "update_metadata", "supersede", "archive"}:
            errors.append(f"{label}: unknown op {op!r}")
            continue
        type_name = operation.get("record_type")
        record_type = TYPE_BY_NAME.get(type_name) if isinstance(type_name, str) else None
        if record_type is None or not record_type.proposable:
            errors.append(f"{label}: unsupported record_type {type_name!r}")
            continue

        evidence = _evidence_ids(proposal, operation)
        if op in SEMANTIC_OPS or evidence:
            _validate_evidence(evidence, records, record_type, label, errors)

        preview_item: dict[str, Any] = {
            "op": op,
            "record_type": record_type.name,
            "evidence": evidence,
        }

        if op == "create":
            record = operation.get("record")
            record_id = _validate_record_identity(record, record_type, label, errors)
            if record_id is None or not isinstance(record, dict):
                continue
            if record_id in records:
                errors.append(f"{label}: id already exists: {record_id}")
                continue
            errors.extend(_record_errors(root, record, record_type, label))
            records[record_id] = copy.deepcopy(record)
            preview_item["record_id"] = record_id
            if record_type.name == "Assertion":
                touched_assertions.add(record_id)

        elif op == "update_metadata":
            target_id = _check_target(
                _target_id(operation, label, errors), records, record_type, label, errors
            )
            fields = operation.get("fields")
            if target_id is None:
                continue
            if not isinstance(fields, dict) or not fields:
                errors.append(f"{label}: fields must be a non-empty object")
                continue
            forbidden = set(fields) - set(record_type.metadata_fields)
            if forbidden:
                names = ", ".join(sorted(forbidden))
                errors.append(f"{label}: fields not allowed for {record_type.name}: {names}")
                continue
            updated = copy.deepcopy(records[target_id])
            updated.update(fields)
            updated["updated_at"] = timestamp
            errors.extend(_record_errors(root, updated, record_type, label))
            records[target_id] = updated
            preview_item["target_id"] = target_id
            preview_item["fields"] = sorted(fields)

        elif op == "archive":
            target_id = _check_target(
                _target_id(operation, label, errors), records, record_type, label, errors
            )
            if target_id is None:
                continue
            if not record_type.archive:
                errors.append(f"{label}: {record_type.name} cannot be archived")
                continue
            updated = copy.deepcopy(records[target_id])
            updated["status"] = "archived"
            updated["updated_at"] = timestamp
            errors.extend(_record_errors(root, updated, record_type, label))
            records[target_id] = updated
            preview_item["target_id"] = target_id

        elif op == "supersede":
            target_id = _check_target(
                _target_id(operation, label, errors), records, record_type, label, errors
            )
            if target_id is None or not record_type.supersede:
                if target_id is not None:
                    errors.append(f"{label}: {record_type.name} cannot be superseded")
                continue
            record = operation.get("record")
            record_id = _validate_record_identity(record, record_type, label, errors)
            if record_id is None or not isinstance(record, dict):
                continue
            if record_id == target_id:
                errors.append(f"{label}: replacement id must differ from target id")
                continue
            if record_id in records:
                errors.append(f"{label}: replacement id already exists: {record_id}")
                continue
            supersedes = record.get("supersedes")
            if not isinstance(supersedes, list) or target_id not in supersedes:
                errors.append(f"{label}: replacement record must include {target_id} in supersedes")
                continue
            if record_type.name == "Assertion":
                transaction = record.get("transaction_time")
                if not isinstance(transaction, dict) or not isinstance(
                    transaction.get("recorded_at"), str
                ):
                    errors.append(
                        f"{label}: assertion replacement needs transaction_time.recorded_at"
                    )
                    continue
                previous = copy.deepcopy(records[target_id])
                previous["status"] = "superseded"
                previous["updated_at"] = timestamp
                previous_transaction = previous.get("transaction_time")
                if not isinstance(previous_transaction, dict):
                    errors.append(f"{label}: target assertion has no transaction_time")
                    continue
                previous_transaction["recorded_until"] = transaction["recorded_at"]
                errors.extend(_record_errors(root, previous, record_type, label))
                records[target_id] = previous
            errors.extend(_record_errors(root, record, record_type, label))
            records[record_id] = copy.deepcopy(record)
            preview_item["target_id"] = target_id
            preview_item["record_id"] = record_id
            if record_type.name == "Assertion":
                touched_assertions.add(record_id)

        preview.append(preview_item)

    if touched_assertions:
        _detect_conflicts(records, touched_assertions, errors)

    archived_path = applied_dir(root) / safe_filename(str(proposal.get("id", "proposal_unknown")))
    if archived_path.exists():
        errors.append(
            f"proposal: applied record already exists: {_record_label(root, archived_path)}"
        )
    archived = copy.deepcopy(proposal)
    archived["status"] = "merged"
    archived["updated_at"] = timestamp
    archived["applied_at"] = timestamp
    archived["approval_state"] = "merged"
    errors.extend(_record_errors(root, archived, proposal_type, "archived proposal"))

    validation_items: list[tuple[Path, dict[str, Any]]] = []
    for record_id, record in records.items():
        path = paths.get(record_id)
        if path is None:
            path = _new_record_path(root, record)
        validation_items.append((path, record))
    validation_items.append((archived_path, archived))
    final_validation = validate.validate_items(root, validation_items)
    errors.extend(final_validation["errors"])

    if errors:
        raise ProposalError(list(dict.fromkeys(errors)))

    writes: dict[Path, dict[str, Any]] = {}
    for record_id, record in records.items():
        if record_id not in original or record != original[record_id]:
            writes[paths.get(record_id) or _new_record_path(root, record)] = record
    writes[archived_path] = archived

    return ApplyPlan(
        proposal=proposal,
        proposal_path=find_proposal(root, str(proposal.get("id"))) or pending_dir(root),
        writes=writes,
        archived_path=archived_path,
        archived_proposal=archived,
        preview=preview,
    )


def _git(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(root), *args],
        capture_output=True,
        text=True,
        check=False,
    )


def _require_clean_git(root: Path) -> None:
    result = _git(root, "rev-parse", "--is-inside-work-tree")
    if result.returncode != 0 or result.stdout.strip() != "true":
        raise ProposalError([f"{root} is not a Git repository; use --no-commit"])
    status = _git(root, "status", "--porcelain", "--untracked-files=no")
    if status.returncode != 0:
        raise ProposalError([f"cannot inspect Git status: {status.stderr.strip()}"])
    if status.stdout.strip():
        changed = ", ".join(line[3:] for line in status.stdout.splitlines() if line.strip())
        raise ProposalError([f"working tree has uncommitted tracked changes: {changed}"])


def _write_plan(plan: ApplyPlan) -> dict[Path, bytes | None]:
    originals: dict[Path, bytes | None] = {}
    for path in plan.writes:
        originals[path] = path.read_bytes() if path.exists() else None
    try:
        for path, record in plan.writes.items():
            path.parent.mkdir(parents=True, exist_ok=True)
            temporary = path.with_name(f".{path.name}.tmp-{os.getpid()}")
            temporary.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
            os.replace(temporary, path)
    except Exception:
        _rollback(originals)
        raise
    return originals


def _rollback(originals: dict[Path, bytes | None]) -> None:
    for path, content in originals.items():
        if content is None:
            path.unlink(missing_ok=True)
        else:
            path.write_bytes(content)


def _commit(root: Path, plan: ApplyPlan, proposal_id: str) -> str:
    rels = [str(path.relative_to(root)) for path in plan.writes]
    added = _git(root, "add", "--", *rels)
    if added.returncode != 0:
        raise ProposalError([f"git add failed: {added.stderr.strip()}"])
    committed = _git(root, "commit", "-m", f"feat(proposal): apply {proposal_id}")
    if committed.returncode != 0:
        raise ProposalError([f"git commit failed: {committed.stderr.strip()}"])
    revision = _git(root, "rev-parse", "HEAD")
    return revision.stdout.strip()


def _result(plan: ApplyPlan, root: Path, commit: str | None, dry_run: bool) -> dict[str, Any]:
    return {
        "ok": True,
        "proposal_id": plan.proposal.get("id"),
        "dry_run": dry_run,
        "commit": commit,
        "operations": plan.preview,
        "files": [
            _record_label(root, path) for path in sorted(plan.writes, key=lambda item: str(item))
        ],
    }


def apply_proposal(
    root: Path,
    proposal_id: str,
    *,
    dry_run: bool = False,
    commit: bool = True,
    now: str | None = None,
) -> dict[str, Any]:
    root = Path(root)
    path = find_proposal(root, proposal_id)
    if path is None:
        raise ProposalError([f"pending proposal not found: {proposal_id}"])
    proposal = _load_json(path)
    if proposal is None:
        raise ProposalError([f"cannot read proposal: {_record_label(root, path)}"])
    plan = plan_apply(root, proposal, now=now)
    plan.proposal_path = path
    if dry_run:
        return _result(plan, root, None, True)
    if commit:
        _require_clean_git(root)
    originals = _write_plan(plan)
    revision: str | None = None
    if commit:
        try:
            revision = _commit(root, plan, proposal_id)
        except Exception:
            _rollback(originals)
            raise
    path.unlink(missing_ok=True)
    return _result(plan, root, revision, False)


def reject_proposal(
    root: Path, proposal_id: str, reason: str | None = None, now: str | None = None
) -> dict[str, Any]:
    root = Path(root)
    path = find_proposal(root, proposal_id)
    if path is None:
        raise ProposalError([f"pending proposal not found: {proposal_id}"])
    proposal = _load_json(path)
    if proposal is None:
        raise ProposalError([f"cannot read proposal: {_record_label(root, path)}"])
    if proposal.get("status") in {"merged", "archived"}:
        raise ProposalError([f"proposal {proposal_id} is already {proposal.get('status')}"])
    proposal["status"] = "rejected"
    proposal["updated_at"] = _now(now)
    if reason:
        proposal["notes"] = reason
    path.write_text(json.dumps(proposal, indent=2) + "\n", encoding="utf-8")
    return {"ok": True, "proposal_id": proposal_id, "status": "rejected"}
