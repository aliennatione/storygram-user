import json
from pathlib import Path

from click.testing import CliRunner

from storygram.cli import main
from storygram.genogram import build_genogram


def make_archive(tmp_path: Path) -> Path:
    (tmp_path / "data" / "assertions").mkdir(parents=True)
    (tmp_path / "data" / "relationships").mkdir(parents=True)
    return tmp_path


def write(root: Path, relative: str, data: dict) -> None:
    path = root / "data" / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data), encoding="utf-8")


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
) -> dict:
    return {
        "id": relationship_id,
        "type": "Relationship",
        "subject": subject,
        "predicate": predicate,
        "object": obj,
        "status": status,
    }


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
