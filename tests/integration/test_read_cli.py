import json
import shutil
from pathlib import Path

from click.testing import CliRunner

from storygram.cli import main


def make_archive(tmp_path: Path) -> Path:
    shutil.copytree(Path("schema"), tmp_path / "schema")
    people = tmp_path / "data" / "people"
    people.mkdir(parents=True)
    (people / "anna.json").write_text(
        json.dumps(
            {
                "id": "person:anna",
                "type": "Person",
                "name": "Anna",
                "status": "reported",
                "created_at": "2026-01-01T00:00:00+00:00",
                "updated_at": "2026-01-01T00:00:00+00:00",
            }
        ),
        encoding="utf-8",
    )
    return tmp_path


def test_get_and_list_accept_archive(tmp_path):
    root = make_archive(tmp_path)
    runner = CliRunner()

    fetched = runner.invoke(main, ["get", "person:anna", "--archive", str(root), "--json"])
    listed = runner.invoke(main, ["list", "--archive", str(root), "--json"])
    filtered = runner.invoke(main, ["list", "--archive", str(root), "--type", "person", "--json"])

    assert fetched.exit_code == 0, fetched.output
    assert json.loads(fetched.output)["id"] == "person:anna"
    assert [item["id"] for item in json.loads(listed.output)] == ["person:anna"]
    assert [item["id"] for item in json.loads(filtered.output)] == ["person:anna"]
