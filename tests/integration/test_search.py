import json
import sqlite3
from pathlib import Path

from click.testing import CliRunner

from storygram.cli import main
from storygram.index import build_index, search


def make_archive(tmp_path: Path) -> Path:
    (tmp_path / "data" / "people").mkdir(parents=True)
    (tmp_path / "data" / "assertions").mkdir(parents=True)
    return tmp_path


def write(root: Path, relative: str, data: dict) -> None:
    path = root / "data" / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data), encoding="utf-8")


def counts(root: Path) -> tuple[int, int]:
    conn = sqlite3.connect(str(root / "generated" / "index.db"))
    try:
        records = conn.execute("SELECT COUNT(*) FROM records").fetchone()[0]
        fts = conn.execute("SELECT COUNT(*) FROM records_fts").fetchone()[0]
    finally:
        conn.close()
    return records, fts


def test_rebuild_is_idempotent_and_drops_deleted_records(tmp_path):
    root = make_archive(tmp_path)
    write(root, "people/anna.json", {"id": "person:anna", "type": "Person", "name": "Anna"})
    write(root, "people/bruno.json", {"id": "person:bruno", "type": "Person", "name": "Bruno"})

    for _ in range(3):
        build_index(root)
        assert counts(root) == (2, 2)

    (root / "data" / "people" / "bruno.json").unlink()
    build_index(root)

    assert counts(root) == (1, 1)
    assert search(root, "Bruno") == []


def test_search_matches_id_type_and_content(tmp_path):
    root = make_archive(tmp_path)
    write(root, "people/anna.json", {"id": "person:anna", "type": "Person", "name": "Anna"})
    write(
        root,
        "assertions/lived.json",
        {
            "id": "assertion:lived",
            "type": "Assertion",
            "subject": "person:anna",
            "predicate": "relation:lived_in",
            "object": "place:brescia",
        },
    )

    assert search(root, "person:anna") == [{"id": "person:anna", "type": "Person"}]
    assert search(root, "Person") == [{"id": "person:anna", "type": "Person"}]
    assert search(root, "relation:lived_in") == [
        {"id": "assertion:lived", "type": "Assertion"}
    ]


def test_search_is_deterministic(tmp_path):
    root = make_archive(tmp_path)
    for name in ("zoe", "anna", "mario"):
        write(root, f"people/{name}.json", {"id": f"person:{name}", "type": "Person", "name": "Smith"})

    assert [r["id"] for r in search(root, "Smith")] == [
        "person:anna",
        "person:mario",
        "person:zoe",
    ]


def test_search_cli_refreshes_stale_index(tmp_path):
    root = make_archive(tmp_path)
    write(root, "people/anna.json", {"id": "person:anna", "type": "Person", "name": "Anna"})
    runner = CliRunner()
    assert runner.invoke(main, ["search", "Anna", "--archive", str(root)]).exit_code == 0

    write(root, "people/bruno.json", {"id": "person:bruno", "type": "Person", "name": "Bruno"})
    result = runner.invoke(main, ["search", "Bruno", "--archive", str(root), "--json"])

    assert result.exit_code == 0, result.output
    assert json.loads(result.output) == [{"id": "person:bruno", "type": "Person"}]


def test_rebuild_reports_malformed_records(tmp_path):
    root = make_archive(tmp_path)
    (root / "data" / "people" / "broken.json").write_text("{not json", encoding="utf-8")

    result = CliRunner().invoke(main, ["rebuild", str(root)])

    assert result.exit_code == 1
    assert "broken.json" in result.output
