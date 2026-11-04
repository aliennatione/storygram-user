import json
from pathlib import Path

from click.testing import CliRunner

from storygram import validate
from storygram.cli import main
from storygram.genogram import build_genogram
from storygram.registry import TYPE_BY_NAME


def make_archive(tmp_path: Path) -> Path:
    (tmp_path / "data" / "assertions").mkdir(parents=True)
    (tmp_path / "data" / "relationships").mkdir(parents=True)
    return tmp_path


def write(root: Path, relative: str, data: dict) -> None:
    path = root / "data" / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data), encoding="utf-8")


def load_fixture(root: Path, name: str) -> Path:
    data = json.loads(Path("tests/fixtures", name).read_text(encoding="utf-8"))
    for record in data["records"]:
        record_type = TYPE_BY_NAME[record["type"]]
        assert validate.validate_instance(root, record, record_type) == []
        filename = f"{record['id'].split(':', 1)[1]}.json"
        path = root / "data" / record_type.directory / filename
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(record), encoding="utf-8")
    return root


def assertion(
    assertion_id: str, subject: str, predicate: str, obj: str, status: str = "reported"
) -> dict:
    return {
        "id": assertion_id,
        "type": "Assertion",
        "subject": subject,
        "predicate": predicate,
        "object": obj,
        "status": status,
    }


def relationship(
    relationship_id: str,
    subject: str | None,
    predicate: str | None,
    obj: str | None,
    status: str = "reported",
    valid_time: dict | None = None,
    transaction_time: dict | None = None,
) -> dict:
    data = {
        "id": relationship_id,
        "type": "Relationship",
        "subject": subject,
        "predicate": predicate,
        "object": obj,
        "status": status,
    }
    if valid_time is not None:
        data["valid_time"] = valid_time
    if transaction_time is not None:
        data["transaction_time"] = transaction_time
    return data


def test_genogram_scopes_assertions_to_person(tmp_path):
    root = make_archive(tmp_path)
    write(
        root,
        "assertions/out.json",
        assertion("assertion:out", "person:anna", "relation:parent", "person:bruno"),
    )
    write(
        root,
        "assertions/in.json",
        assertion("assertion:in", "person:carla", "relation:parent", "person:anna"),
    )
    write(
        root,
        "assertions/other.json",
        assertion("assertion:other", "person:bruno", "relation:parent", "person:carla"),
    )

    result = build_genogram(root, "person:anna")

    assert [item["assertion_id"] for item in result["relations"]] == [
        "assertion:in",
        "assertion:out",
    ]
    assert [item["direction"] for item in result["relations"]] == ["incoming", "outgoing"]
    assert all(item["supported"] for item in result["relations"])


def test_genogram_includes_endpoint_aware_relationship_records(tmp_path):
    root = make_archive(tmp_path)
    write(
        root,
        "relationships/out.json",
        relationship("relationship:out", "person:anna", "relation:parent", "person:bruno"),
    )
    write(
        root,
        "relationships/in.json",
        relationship("relationship:in", "person:carla", "relation:parent", "person:anna"),
    )
    write(
        root,
        "relationships/other.json",
        relationship("relationship:other", "person:bruno", "relation:parent", "person:carla"),
    )

    result = build_genogram(root, "person:anna")

    assert [item["relationship_id"] for item in result["relations"]] == [
        "relationship:in",
        "relationship:out",
    ]
    assert [item["record_type"] for item in result["relations"]] == [
        "Relationship",
        "Relationship",
    ]
    assert [item["direction"] for item in result["relations"]] == ["incoming", "outgoing"]
    assert all(item["supported"] for item in result["relations"])


def test_genogram_deduplicates_equivalent_relationship_and_assertion(tmp_path):
    root = make_archive(tmp_path)
    write(
        root,
        "relationships/parent.json",
        relationship("relationship:parent", "person:anna", "relation:parent", "person:bruno"),
    )
    write(
        root,
        "assertions/parent.json",
        assertion("assertion:parent", "person:anna", "relation:parent", "person:bruno"),
    )
    write(
        root,
        "assertions/parent-copy.json",
        assertion("assertion:parent-copy", "person:anna", "relation:parent", "person:bruno"),
    )

    result = build_genogram(root, "person:anna")

    assert len(result["relations"]) == 1
    relation = result["relations"][0]
    assert relation["record_type"] == "Relationship"
    assert relation["record_id"] == "relationship:parent"
    assert relation["relationship_id"] == "relationship:parent"
    assert relation["related_ids"] == [
        "assertion:parent",
        "assertion:parent-copy",
        "relationship:parent",
    ]
    assert relation["valid_times"] == []
    assert relation["transaction_times"] == []


def test_genogram_keeps_distinct_predicates_for_same_endpoints(tmp_path):
    root = make_archive(tmp_path)
    write(
        root,
        "assertions/parent.json",
        assertion("assertion:parent", "person:anna", "relation:parent", "person:bruno"),
    )
    write(
        root,
        "assertions/spouse.json",
        assertion("assertion:spouse", "person:anna", "relation:spouse", "person:bruno"),
    )

    result = build_genogram(root, "person:anna")

    assert [item["assertion_id"] for item in result["relations"]] == [
        "assertion:parent",
        "assertion:spouse",
    ]


def test_genogram_exposes_relationship_temporal_fields(tmp_path):
    root = make_archive(tmp_path)
    write(
        root,
        "relationships/parent.json",
        relationship(
            "relationship:parent",
            "person:anna",
            "relation:parent",
            "person:bruno",
            valid_time={"start": "1987", "end": "1995", "precision": "year"},
            transaction_time={
                "recorded_at": "2026-01-01T00:00:00+00:00",
                "recorded_until": None,
            },
        ),
    )

    result = build_genogram(root, "person:anna")

    relation = result["relations"][0]
    assert relation["valid_time"] == {"start": "1987", "end": "1995", "precision": "year"}
    assert relation["transaction_time"] == {
        "recorded_at": "2026-01-01T00:00:00+00:00",
        "recorded_until": None,
    }
    assert relation["valid_times"] == [{"start": "1987", "end": "1995", "precision": "year"}]
    assert relation["transaction_times"] == [
        {
            "recorded_at": "2026-01-01T00:00:00+00:00",
            "recorded_until": None,
        }
    ]


def test_genogram_realistic_family_fixture_aggregates_temporal_intervals(tmp_path):
    root = load_fixture(tmp_path, "genogram_family.json")

    result = build_genogram(root, "person:anna")

    relations = result["relations"]
    assert len(relations) == 4
    assert all(item["record_id"] != "relationship:anna-davide-archived" for item in relations)

    spouse = next(item for item in relations if item["predicate"] == "relation:spouse")
    assert spouse["record_id"] == "relationship:anna-bruno-2000"
    assert spouse["valid_time"] == {"start": "2000", "end": "2010", "precision": "year"}
    assert spouse["valid_times"] == [
        {"start": "1980", "end": "1990", "precision": "year"},
        {"start": "2000", "end": "2010", "precision": "year"},
    ]
    assert spouse["transaction_times"] == [
        {"recorded_at": "2026-01-01T00:00:00+00:00", "recorded_until": None},
        {"recorded_at": "2026-02-01T00:00:00+00:00", "recorded_until": None},
    ]
    assert spouse["related_ids"] == [
        "relationship:anna-bruno-1980",
        "relationship:anna-bruno-2000",
    ]

    parent = next(
        item
        for item in relations
        if item["predicate"] == "relation:parent" and item["direction"] == "outgoing"
    )
    assert parent["record_id"] == "relationship:anna-carla"
    assert parent["valid_times"] == [{"start": "1987", "precision": "year"}]
    assert parent["transaction_times"] == [
        {"recorded_at": "2026-01-01T00:00:00+00:00", "recorded_until": None},
        {"recorded_at": "2026-03-01T00:00:00+00:00", "recorded_until": None},
    ]
    assert parent["related_ids"] == ["assertion:anna-carla", "relationship:anna-carla"]

    incoming = next(item for item in relations if item["direction"] == "incoming")
    assert incoming["record_id"] == "relationship:davide-anna"
    assert incoming["valid_times"] == []

    lived = next(item for item in relations if item["predicate"] == "relation:lived_in")
    assert lived["supported"] is False
    assert "Unsupported relation predicate: relation:lived_in" in result["warnings"]


def test_genogram_warns_on_incomplete_relationship_endpoints(tmp_path):
    root = make_archive(tmp_path)
    write(root, "relationships/family.json", relationship("relationship:family", None, None, None))
    write(
        root,
        "assertions/out.json",
        assertion("assertion:out", "person:anna", "relation:parent", "person:bruno"),
    )

    result = build_genogram(root, "person:anna")

    assert [item["assertion_id"] for item in result["relations"]] == ["assertion:out"]
    assert any("complete endpoints" in warning for warning in result["warnings"])


def test_genogram_skips_closed_relations(tmp_path):
    root = make_archive(tmp_path)
    write(
        root,
        "relationships/archived.json",
        relationship(
            "relationship:archived", "person:anna", "relation:parent", "person:bruno", "archived"
        ),
    )
    write(
        root,
        "assertions/superseded.json",
        assertion(
            "assertion:superseded",
            "person:anna",
            "relation:parent",
            "person:carla",
            "superseded",
        ),
    )

    result = build_genogram(root, "person:anna")

    assert result["relations"] == []


def test_genogram_keeps_unsupported_relations_as_warnings(tmp_path):
    root = make_archive(tmp_path)
    write(
        root,
        "assertions/lived.json",
        assertion("assertion:lived", "person:anna", "relation:lived_in", "place:turin"),
    )

    result = build_genogram(root, "person:anna")

    assert result["relations"][0]["supported"] is False
    assert "Unsupported relation predicate: relation:lived_in" in result["warnings"]


def test_genogram_cli_marks_experimental_and_shows_warnings(tmp_path):
    root = make_archive(tmp_path)
    write(
        root,
        "assertions/lived.json",
        assertion("assertion:lived", "person:anna", "relation:lived_in", "place:turin"),
    )
    runner = CliRunner()

    result = runner.invoke(main, ["genogram", "person:anna", "--archive", str(root)])
    help_result = runner.invoke(main, ["genogram", "--help"])

    assert result.exit_code == 0, result.output
    assert "WARNING: Unsupported relation predicate" in result.output
    assert "experimental" in help_result.output
