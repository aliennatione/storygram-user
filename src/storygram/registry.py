"""Central registry for canonical record types, paths and proposal policies."""

from __future__ import annotations

import re
from collections.abc import Iterator
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class RecordType:
    """Metadata and mutation policy for one canonical record type."""

    name: str
    directory: str
    schema_file: str
    id_prefix: str
    supersede: bool = False
    archive: bool = True
    metadata_fields: tuple[str, ...] = ("tags", "notes", "visibility")
    evidence_required: bool = True
    is_evidence: bool = False
    proposable: bool = True


RECORD_TYPES: tuple[RecordType, ...] = (
    RecordType(
        name="Episode",
        directory="episodes",
        schema_file="episode.schema.json",
        id_prefix="episode",
        supersede=True,
        metadata_fields=("tags", "notes", "visibility"),
        evidence_required=False,
        is_evidence=True,
    ),
    RecordType(
        name="Assertion",
        directory="assertions",
        schema_file="assertion.schema.json",
        id_prefix="assertion",
        supersede=True,
        metadata_fields=("tags", "notes", "visibility"),
    ),
    RecordType(
        name="Person",
        directory="people",
        schema_file="person.schema.json",
        id_prefix="person",
        metadata_fields=("notes", "visibility"),
    ),
    RecordType(
        name="Organization",
        directory="organizations",
        schema_file="organization.schema.json",
        id_prefix="organization",
        metadata_fields=("notes", "visibility"),
    ),
    RecordType(
        name="Place",
        directory="places",
        schema_file="place.schema.json",
        id_prefix="place",
        metadata_fields=("notes", "visibility"),
    ),
    RecordType(
        name="Period",
        directory="periods",
        schema_file="period.schema.json",
        id_prefix="period",
        metadata_fields=("notes", "visibility"),
    ),
    RecordType(
        name="Event",
        directory="events",
        schema_file="event.schema.json",
        id_prefix="event",
        metadata_fields=("notes", "visibility"),
    ),
    RecordType(
        name="Relationship",
        directory="relationships",
        schema_file="relationship.schema.json",
        id_prefix="relationship",
        metadata_fields=("notes", "visibility"),
    ),
    RecordType(
        name="Source",
        directory="sources",
        schema_file="source.schema.json",
        id_prefix="source",
        metadata_fields=("notes", "visibility"),
        is_evidence=True,
    ),
    RecordType(
        name="MediaAsset",
        directory="media-assets",
        schema_file="media-asset.schema.json",
        id_prefix="media",
        metadata_fields=("notes", "visibility"),
    ),
    RecordType(
        name="Annotation",
        directory="annotations",
        schema_file="annotation.schema.json",
        id_prefix="annotation",
        metadata_fields=("notes", "visibility"),
        is_evidence=True,
    ),
    RecordType(
        name="Narrative",
        directory="narratives",
        schema_file="narrative.schema.json",
        id_prefix="narrative",
        metadata_fields=("notes", "visibility"),
    ),
    RecordType(
        name="Collection",
        directory="collections",
        schema_file="collection.schema.json",
        id_prefix="collection",
        metadata_fields=("notes", "visibility"),
    ),
    RecordType(
        name="Conflict",
        directory="conflicts",
        schema_file="conflict.schema.json",
        id_prefix="conflict",
        archive=False,
        metadata_fields=(
            "status",
            "review",
            "evidence",
            "reviewer",
            "decision",
            "notes",
            "visibility",
        ),
    ),
    RecordType(
        name="Proposal",
        directory="proposals",
        schema_file="proposal.schema.json",
        id_prefix="proposal",
        archive=False,
        metadata_fields=("notes",),
        proposable=False,
    ),
)

TYPE_BY_NAME: dict[str, RecordType] = {rt.name: rt for rt in RECORD_TYPES}
PROPOSABLE_TYPES: tuple[RecordType, ...] = tuple(rt for rt in RECORD_TYPES if rt.proposable)
EVIDENCE_TYPE_NAMES: frozenset[str] = frozenset(rt.name for rt in RECORD_TYPES if rt.is_evidence)
REFERENCE_PREFIXES: frozenset[str] = frozenset(rt.id_prefix for rt in RECORD_TYPES)
REFERENCE_RE = re.compile(
    r"^("
    + "|".join(sorted(REFERENCE_PREFIXES, key=len, reverse=True))
    + r"):[A-Za-z0-9][A-Za-z0-9._~-]*$"
)
OP_TYPES = ("create", "update_metadata", "supersede", "archive")


def type_for_id(record_id: str) -> RecordType | None:
    """Return the record type matching an ID prefix, if any."""
    prefix, sep, _ = record_id.partition(":")
    if not sep:
        return None
    return next((rt for rt in RECORD_TYPES if rt.id_prefix == prefix), None)


def schema_paths(root: Any, record_type: RecordType) -> list[Any]:
    """Return schema lookup paths for an archive root.

    Archives initialized by Storygram contain a local ``schema/`` directory.
    Tests and ad-hoc archives may rely on the repository copy instead.
    """
    from pathlib import Path

    root_path = Path(root)
    repo_schema = Path(__file__).resolve().parents[2] / "schema"
    return [
        root_path / "schema" / record_type.schema_file,
        root_path / record_type.schema_file,
        repo_schema / record_type.schema_file,
    ]


def iter_reference_strings(
    value: Any, skip_keys: tuple[str, ...] = ("id", "type")
) -> Iterator[str]:
    """Yield every string value that looks like a canonical record reference."""
    if isinstance(value, dict):
        for key, child in value.items():
            if key in skip_keys:
                continue
            yield from iter_reference_strings(child, skip_keys)
    elif isinstance(value, list):
        for child in value:
            yield from iter_reference_strings(child, skip_keys)
    elif isinstance(value, str) and REFERENCE_RE.match(value):
        yield value
