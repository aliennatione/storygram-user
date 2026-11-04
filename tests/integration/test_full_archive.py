from __future__ import annotations

import json
from pathlib import Path

from storygram import export as export_mod
from storygram import genogram as genogram_mod
from storygram import timeline as timeline_mod
from storygram import validate as validate_mod
from storygram.conflicts import list_conflicts

NOW = "2026-10-30T12:00:00+00:00"


def w(root: Path, directory: str, filename: str, data: dict) -> None:
    path = root / "data" / directory / filename
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data), encoding="utf-8")


def full_archive(root: Path) -> None:
    w(
        root,
        "episodes",
        "episode_1.json",
        {
            "id": "episode:memory",
            "type": "Episode",
            "episode_type": "memory",
            "status": "reported",
            "created_at": NOW,
            "updated_at": NOW,
            "content": {"text": "Family memory."},
        },
    )
    w(
        root,
        "sources",
        "source_1.json",
        {
            "id": "source:register",
            "type": "Source",
            "title": "Register",
            "status": "reported",
            "created_at": NOW,
            "updated_at": NOW,
        },
    )
    w(
        root,
        "people",
        "person_anna.json",
        {
            "id": "person:anna",
            "type": "Person",
            "name": "Anna",
            "status": "confirmed",
            "created_at": NOW,
            "updated_at": NOW,
        },
    )
    w(
        root,
        "people",
        "person_luca.json",
        {
            "id": "person:luca",
            "type": "Person",
            "name": "Luca",
            "status": "confirmed",
            "created_at": NOW,
            "updated_at": NOW,
        },
    )
    w(
        root,
        "places",
        "place_torino.json",
        {
            "id": "place:torino",
            "type": "Place",
            "name": "Torino",
            "status": "confirmed",
            "created_at": NOW,
            "updated_at": NOW,
        },
    )
    w(
        root,
        "events",
        "event_birth.json",
        {
            "id": "event:birth",
            "type": "Event",
            "name": "Birth",
            "status": "confirmed",
            "created_at": NOW,
            "updated_at": NOW,
        },
    )
    w(
        root,
        "organizations",
        "org_family.json",
        {
            "id": "organization:family",
            "type": "Organization",
            "name": "Family",
            "status": "confirmed",
            "created_at": NOW,
            "updated_at": NOW,
        },
    )
    w(
        root,
        "periods",
        "period_childhood.json",
        {
            "id": "period:childhood",
            "type": "Period",
            "name": "Childhood",
            "status": "confirmed",
            "created_at": NOW,
            "updated_at": NOW,
        },
    )
    w(
        root,
        "collections",
        "collection_family.json",
        {
            "id": "collection:family",
            "type": "Collection",
            "name": "Family collection",
            "status": "confirmed",
            "created_at": NOW,
            "updated_at": NOW,
        },
    )
    w(
        root,
        "relationships",
        "rel_parent.json",
        {
            "id": "relationship:parent",
            "type": "Relationship",
            "subject": "person:anna",
            "predicate": "relation:parent",
            "object": "person:luca",
            "status": "confirmed",
            "created_at": NOW,
            "updated_at": NOW,
            "valid_time": {"start": "1990", "precision": "year"},
            "transaction_time": {"recorded_at": NOW},
        },
    )
    w(
        root,
        "assertions",
        "assertion_parent.json",
        {
            "id": "assertion:parent",
            "type": "Assertion",
            "subject": "person:anna",
            "predicate": "relation:parent",
            "object": "person:luca",
            "status": "reported",
            "created_at": NOW,
            "updated_at": NOW,
            "transaction_time": {"recorded_at": NOW},
            "produced_by": ["episode:memory"],
            "supported_by": ["source:register"],
        },
    )
    w(
        root,
        "assertions",
        "assertion_member.json",
        {
            "id": "assertion:member",
            "type": "Assertion",
            "subject": "person:luca",
            "predicate": "relation:member_of",
            "object": "collection:family",
            "status": "reported",
            "created_at": NOW,
            "updated_at": NOW,
            "transaction_time": {"recorded_at": NOW},
        },
    )
    w(
        root,
        "annotations",
        "annotation_1.json",
        {
            "id": "annotation:note",
            "type": "Annotation",
            "status": "reported",
            "created_at": NOW,
            "updated_at": NOW,
            "target_ids": ["person:anna"],
            "episode_ids": ["episode:memory"],
        },
    )
    w(
        root,
        "narratives",
        "narrative_1.json",
        {
            "id": "narrative:story",
            "type": "Narrative",
            "status": "reported",
            "created_at": NOW,
            "updated_at": NOW,
            "author": "Anna",
            "related_ids": ["person:anna"],
        },
    )
    w(
        root,
        "media-assets",
        "media_1.json",
        {
            "id": "media:asset-1",
            "type": "MediaAsset",
            "status": "reported",
            "created_at": NOW,
            "updated_at": NOW,
            "visibility": "family",
            "notes": "photo",
        },
    )
    w(
        root,
        "conflicts",
        "conflict_1.json",
        {
            "id": "conflict:1",
            "type": "Conflict",
            "assertions": ["assertion:parent", "assertion:parent2"],
            "status": "open",
            "created_at": NOW,
            "updated_at": NOW,
            "relation": "contradicts",
            "reason": "competing",
        },
    )
    # competing assertion for conflict detection
    w(
        root,
        "assertions",
        "assertion_parent2.json",
        {
            "id": "assertion:parent2",
            "type": "Assertion",
            "subject": "person:anna",
            "predicate": "relation:parent",
            "object": "person:luca",
            "status": "reported",
            "created_at": NOW,
            "updated_at": NOW,
            "transaction_time": {"recorded_at": NOW},
            "value": "different",
        },
    )


def test_full_archive_validates_and_derives(tmp_path: Path) -> None:
    root = tmp_path
    (root / "data").mkdir()
    from click.testing import CliRunner

    from storygram.cli import main

    CliRunner().invoke(main, ["init", str(root)])
    full_archive(root)

    result = validate_mod.validate_archive(root)
    assert result["ok"], result

    # timeline scopes
    archive_tl = timeline_mod.build_timeline(root)
    assert len(archive_tl) >= 1
    entity_tl = timeline_mod.build_timeline(root, "person:anna")
    assert isinstance(entity_tl, list)
    collection_tl = timeline_mod.build_timeline(root, "collection:family")
    assert any(e.get("assertion_id") == "assertion:member" for e in collection_tl)

    # genogram
    gen = genogram_mod.build_genogram(root, "person:anna")
    assert gen["relations"], gen
    assert gen["relations"][0]["related_ids"]

    # conflicts: explicit + derived
    conflicts = list_conflicts(root)
    assert len(conflicts) >= 1

    # export round trips
    records, _ = validate_mod.load_records(root)
    exported = export_mod.export_json(root)
    json_text = json.dumps(exported)
    records, _ = validate_mod.load_records(root)
    data = [r for _, r in records]
    parsed = export_mod.records_from_json(json_text)
    assert len(parsed) == len(data)
    yaml_text = export_mod.export_yaml(root)
    assert export_mod.records_from_yaml(yaml_text)
    md_text = export_mod.export_markdown(root)
    assert export_mod.records_from_markdown(md_text)
