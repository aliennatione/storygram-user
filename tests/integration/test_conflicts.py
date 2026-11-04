import json
from pathlib import Path

from click.testing import CliRunner

from storygram.cli import main
from storygram.conflicts import list_conflicts


def make_archive(tmp_path: Path) -> Path:
    (tmp_path / "data" / "assertions").mkdir(parents=True)
    (tmp_path / "data" / "conflicts").mkdir(parents=True)
    return tmp_path


def write(root: Path, relative: str, data: dict) -> None:
    path = root / "data" / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data), encoding="utf-8")


def assertion(assertion_id: str, contradicts: list[str] | None = None) -> dict:
    return {
        "id": assertion_id,
        "type": "Assertion",
        "subject": "person:anna",
        "predicate": "relation:lived_in",
        "object": "place:turin",
        "status": "reported",
        "produced_by": [f"episode:{assertion_id.split(':')[1]}"],
        "supported_by": [f"source:{assertion_id.split(':')[1]}"],
        "contradicts": contradicts or [],
    }


def test_list_conflicts_merges_explicit_and_derived(tmp_path):
    root = make_archive(tmp_path)
    write(root, "assertions/a1.json", assertion("assertion:a1", ["assertion:a2"]))
    write(root, "assertions/a2.json", assertion("assertion:a2", ["assertion:a1"]))
    write(
        root,
        "conflicts/explicit.json",
        {
            "id": "conflict:explicit",
            "type": "Conflict",
            "assertions": ["assertion:a1", "assertion:a2"],
            "status": "under_review",
        },
    )

    results = list_conflicts(root)

    assert [item["id"] for item in results] == ["conflict:explicit"]
    assert results[0]["status"] == "under_review"


def test_derived_conflicts_are_deduplicated_and_include_evidence(tmp_path):
    root = make_archive(tmp_path)
    write(root, "assertions/a1.json", assertion("assertion:a1", ["assertion:a2"]))
    write(root, "assertions/a2.json", assertion("assertion:a2", ["assertion:a1"]))

    results = list_conflicts(root)

    assert len(results) == 1
    assert results[0]["id"] == "derived:assertion:a1+assertion:a2"
    assert results[0]["derived"] is True
    assert results[0]["evidence"] == ["episode:a1", "episode:a2", "source:a1", "source:a2"]
    assert {record["id"] for record in results[0]["assertion_records"]} == {
        "assertion:a1",
        "assertion:a2",
    }


def test_status_filter_applies_to_derived_conflicts(tmp_path):
    root = make_archive(tmp_path)
    write(root, "assertions/a1.json", assertion("assertion:a1", ["assertion:a2"]))
    write(root, "assertions/a2.json", assertion("assertion:a2"))

    assert list_conflicts(root, "open")[0]["status"] == "open"
    assert list_conflicts(root, "resolved") == []


def test_conflicts_cli_shows_derived_marker(tmp_path):
    root = make_archive(tmp_path)
    write(root, "assertions/a1.json", assertion("assertion:a1", ["assertion:a2"]))
    write(root, "assertions/a2.json", assertion("assertion:a2"))

    result = CliRunner().invoke(main, ["conflicts", "--archive", str(root)])

    assert result.exit_code == 0, result.output
    assert "[derived]" in result.output
    assert "assertions: assertion:a1, assertion:a2" in result.output
