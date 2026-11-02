import json
from pathlib import Path

from click.testing import CliRunner
from jsonschema import validate

from storygram.cli import main


def test_ingest_episode_does_not_confirm():
    ep_schema = json.loads(Path("schema/episode.schema.json").read_text())
    ep = json.loads(Path("tests/fixtures/episode_interview.json").read_text())
    validate(instance=ep, schema=ep_schema)
    # Episode status is reported/not confirmed; ingestion should not create confirmed facts
    assert ep["status"] != "confirmed"


def make_archive(tmp_path: Path) -> Path:
    (tmp_path / "inbox").mkdir()
    (tmp_path / "data" / "episodes").mkdir(parents=True)
    return tmp_path


def test_ingest_copies_to_inbox_only(tmp_path):
    root = make_archive(tmp_path)
    source = tmp_path / "interview.txt"
    source.write_text("synthetic capture", encoding="utf-8")

    result = CliRunner().invoke(main, ["ingest", "episode", str(source), "--archive", str(root)])

    assert result.exit_code == 0, result.output
    assert (root / "inbox" / "interview.txt").read_text(encoding="utf-8") == "synthetic capture"
    assert list((root / "data" / "episodes").iterdir()) == []


def test_ingest_invalid_episode_never_reaches_data(tmp_path):
    root = make_archive(tmp_path)
    source = tmp_path / "bad.json"
    source.write_text('{"id": "episode:bad", "type": "Episode"}', encoding="utf-8")

    result = CliRunner().invoke(main, ["ingest", "episode", str(source), "--archive", str(root)])

    assert result.exit_code == 0, result.output
    assert (root / "inbox" / "bad.json").exists()
    assert list((root / "data" / "episodes").iterdir()) == []


def test_ingest_refuses_silent_overwrite(tmp_path):
    root = make_archive(tmp_path)
    first = tmp_path / "one" / "capture.txt"
    second = tmp_path / "two" / "capture.txt"
    first.parent.mkdir()
    second.parent.mkdir()
    first.write_text("first", encoding="utf-8")
    second.write_text("second", encoding="utf-8")
    runner = CliRunner()

    assert (
        runner.invoke(main, ["ingest", "episode", str(first), "--archive", str(root)]).exit_code
        == 0
    )
    result = runner.invoke(main, ["ingest", "episode", str(second), "--archive", str(root)])

    assert result.exit_code == 1
    assert "already exists" in result.output
    assert (root / "inbox" / "capture.txt").read_text(encoding="utf-8") == "first"

    result = runner.invoke(
        main, ["ingest", "episode", str(second), "--archive", str(root), "--overwrite"]
    )
    assert result.exit_code == 0, result.output
    assert (root / "inbox" / "capture.txt").read_text(encoding="utf-8") == "second"


def test_ingest_old_file_grammar_is_rejected(tmp_path):
    root = make_archive(tmp_path)
    source = tmp_path / "capture.txt"
    source.write_text("synthetic", encoding="utf-8")

    result = CliRunner().invoke(main, ["ingest", str(source), "--archive", str(root)])

    assert result.exit_code != 0
