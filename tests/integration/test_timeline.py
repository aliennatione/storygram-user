import json
from pathlib import Path

from click.testing import CliRunner

from storygram.cli import main
from storygram.timeline import build_timeline


def make_archive(tmp_path: Path) -> Path:
    (tmp_path / "data" / "assertions").mkdir(parents=True)
    (tmp_path / "data" / "people").mkdir(parents=True)
    return tmp_path


def write(root: Path, relative: str, data: dict) -> None:
    path = root / "data" / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data), encoding="utf-8")


def assertion(assertion_id: str, status: str, start: str) -> dict:
    return {
        "id": assertion_id,
        "type": "Assertion",
        "subject": "person:anna",
        "predicate": "relation:lived_in",
        "object": "place:turin",
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
