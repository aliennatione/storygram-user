import json
from pathlib import Path

from click.testing import CliRunner

from storygram.cli import main
from storygram.timeline import build_timeline


def make_archive(tmp_path: Path) -> Path:
    (tmp_path / "data" / "assertions").mkdir(parents=True)
    (tmp_path / "data" / "people").mkdir(parents=True)
    (tmp_path / "data" / "collections").mkdir(parents=True)
    return tmp_path


def write(root: Path, relative: str, data: dict) -> None:
    path = root / "data" / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data), encoding="utf-8")


def assertion(
    assertion_id: str,
    status: str,
    start: str,
    subject: str = "person:anna",
    predicate: str = "relation:lived_in",
    obj: str = "place:turin",
) -> dict:
    return {
        "id": assertion_id,
        "type": "Assertion",
        "subject": subject,
        "predicate": predicate,
        "object": obj,
        "status": status,
        "valid_time": {"start": start, "end": None, "precision": "year"},
        "transaction_time": {"recorded_at": "2026-01-01T00:00:00+00:00", "recorded_until": None},
        "produced_by": [f"episode:{assertion_id.split(':')[1]}"],
        "supported_by": [f"source:{assertion_id.split(':')[1]}"],
    }


def test_timeline_excludes_closed_assertions_and_sorts(tmp_path):
    root = make_archive(tmp_path)
    write(root, "assertions/late.json", assertion("assertion:late", "reported", "2000"))
    write(root, "assertions/early.json", assertion("assertion:early", "disputed", "1987"))
    write(root, "assertions/old.json", assertion("assertion:old", "superseded", "1970"))
    write(root, "assertions/archived.json", assertion("assertion:archived", "archived", "1960"))
    write(root, "assertions/rejected.json", assertion("assertion:rejected", "rejected", "1950"))

    result = build_timeline(root, "person:anna")

    assert [item["assertion_id"] for item in result] == ["assertion:early", "assertion:late"]
    assert result[0]["produced_by"] == ["episode:early"]
    assert result[0]["supported_by"] == ["source:early"]
    assert result[0]["transaction_time"]["recorded_until"] is None


def test_timeline_includes_object_side_matches(tmp_path):
    root = make_archive(tmp_path)
    write(root, "assertions/place.json", assertion("assertion:place", "reported", "1990"))

    assert [item["assertion_id"] for item in build_timeline(root, "place:turin")] == [
        "assertion:place"
    ]


def test_timeline_archive_level_includes_every_open_assertion(tmp_path):
    root = make_archive(tmp_path)
    write(root, "assertions/late.json", assertion("assertion:late", "reported", "2000"))
    write(
        root,
        "assertions/other.json",
        assertion("assertion:other", "reported", "1987", subject="person:bruno"),
    )
    write(root, "assertions/old.json", assertion("assertion:old", "superseded", "1970"))

    result = build_timeline(root)

    assert [item["assertion_id"] for item in result] == ["assertion:other", "assertion:late"]


def test_timeline_collection_level_includes_members_and_collection_links(tmp_path):
    root = make_archive(tmp_path)
    write(
        root,
        "collections/family.json",
        {
            "id": "collection:family",
            "type": "Collection",
            "name": "Family",
            "status": "confirmed",
            "created_at": "2026-01-01T00:00:00+00:00",
            "updated_at": "2026-01-01T00:00:00+00:00",
        },
    )
    write(
        root,
        "assertions/membership.json",
        assertion(
            "assertion:membership",
            "reported",
            "1980",
            subject="person:anna",
            predicate="relation:member_of",
            obj="collection:family",
        ),
    )
    write(root, "assertions/member.json", assertion("assertion:member", "reported", "1987"))
    write(
        root,
        "assertions/collection.json",
        assertion(
            "assertion:collection",
            "reported",
            "1970",
            subject="collection:family",
            predicate="relation:documented_in",
            obj="source:album",
        ),
    )
    write(
        root,
        "assertions/non-member.json",
        assertion("assertion:non-member", "reported", "1990", subject="person:bruno"),
    )

    result = build_timeline(root, "collection:family")

    assert [item["assertion_id"] for item in result] == [
        "assertion:collection",
        "assertion:membership",
        "assertion:member",
    ]


def test_timeline_collection_level_ignores_closed_membership(tmp_path):
    root = make_archive(tmp_path)
    write(
        root,
        "assertions/membership.json",
        assertion(
            "assertion:membership",
            "superseded",
            "1980",
            subject="person:anna",
            predicate="relation:member_of",
            obj="collection:family",
        ),
    )
    write(root, "assertions/member.json", assertion("assertion:member", "reported", "1987"))

    assert build_timeline(root, "collection:family") == []


def test_timeline_cli_reports_known_empty_and_unknown(tmp_path):
    root = make_archive(tmp_path)
    write(root, "people/anna.json", {"id": "person:anna", "type": "Person"})
    runner = CliRunner()

    empty = runner.invoke(main, ["timeline", "person:anna", "--archive", str(root)])
    unknown = runner.invoke(main, ["timeline", "person:nobody", "--archive", str(root)])

    assert empty.exit_code == 0, empty.output
    assert "No timeline entries for person:anna" in empty.output
    assert unknown.exit_code == 1
    assert "Unknown record: person:nobody" in unknown.output


def test_timeline_cli_archive_and_collection_scopes(tmp_path):
    root = make_archive(tmp_path)
    write(
        root,
        "collections/family.json",
        {"id": "collection:family", "type": "Collection"},
    )
    write(
        root,
        "assertions/membership.json",
        assertion(
            "assertion:membership",
            "reported",
            "1980",
            subject="person:anna",
            predicate="relation:member_of",
            obj="collection:family",
        ),
    )
    write(
        root,
        "assertions/other.json",
        assertion("assertion:other", "reported", "1990", subject="person:bruno"),
    )
    runner = CliRunner()

    archive = runner.invoke(main, ["timeline", "--all", "--archive", str(root), "--json"])
    collection = runner.invoke(
        main, ["timeline", "collection:family", "--archive", str(root), "--json"]
    )
    missing_scope = runner.invoke(main, ["timeline", "--archive", str(root)])
    conflicting_scope = runner.invoke(
        main, ["timeline", "person:anna", "--all", "--archive", str(root)]
    )

    assert archive.exit_code == 0, archive.output
    assert [item["assertion_id"] for item in json.loads(archive.output)] == [
        "assertion:membership",
        "assertion:other",
    ]
    assert collection.exit_code == 0, collection.output
    assert [item["assertion_id"] for item in json.loads(collection.output)] == [
        "assertion:membership"
    ]
    assert missing_scope.exit_code == 1
    assert "Provide either a record ID or --all" in missing_scope.output
    assert conflicting_scope.exit_code == 1
    assert "Provide either a record ID or --all" in conflicting_scope.output


def test_timeline_cli_archive_empty(tmp_path):
    root = make_archive(tmp_path)
    runner = CliRunner()

    result = runner.invoke(main, ["timeline", "--all", "--archive", str(root)])

    assert result.exit_code == 0, result.output
    assert "No timeline entries in archive" in result.output
