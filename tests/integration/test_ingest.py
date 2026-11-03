import hashlib
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


def capture_metadata(root: Path, filename: str) -> dict:
    path = root / "inbox" / ".storygram" / f"{filename}.json"
    return json.loads(path.read_text(encoding="utf-8"))


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


def test_ingest_writes_checksum_metadata_sidecar(tmp_path):
    root = make_archive(tmp_path)
    source = tmp_path / "interview.txt"
    content = "synthetic capture"
    source.write_text(content, encoding="utf-8")

    result = CliRunner().invoke(main, ["ingest", "episode", str(source), "--archive", str(root)])

    assert result.exit_code == 0, result.output
    metadata = capture_metadata(root, "interview.txt")
    assert metadata["format"] == "storygram.capture/1"
    assert metadata["filename"] == "interview.txt"
    assert metadata["size"] == len(content.encode("utf-8"))
    assert metadata["mime_type"] == "text/plain"
    assert metadata["checksum"] == {
        "algorithm": "sha256",
        "value": hashlib.sha256(content.encode("utf-8")).hexdigest(),
    }
    assert metadata["overwritten"] is False
    assert metadata["ingested_at"].endswith("+00:00")
    assert list((root / "data" / "episodes").iterdir()) == []


def test_ingest_metadata_stays_in_inbox_for_binary_content(tmp_path):
    root = make_archive(tmp_path)
    source = tmp_path / "sound.bin"
    content = bytes(range(256)) * 3
    source.write_bytes(content)

    result = CliRunner().invoke(main, ["ingest", "episode", str(source), "--archive", str(root)])

    assert result.exit_code == 0, result.output
    metadata = capture_metadata(root, "sound.bin")
    assert metadata["size"] == len(content)
    assert metadata["checksum"]["value"] == hashlib.sha256(content).hexdigest()
    assert (root / "inbox" / "sound.bin").read_bytes() == content
    assert list((root / "data").rglob("*")) == [root / "data" / "episodes"]


def test_ingest_overwrite_refreshes_checksum_metadata(tmp_path):
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
    result = runner.invoke(
        main, ["ingest", "episode", str(second), "--archive", str(root), "--overwrite"]
    )

    assert result.exit_code == 0, result.output
    metadata = capture_metadata(root, "capture.txt")
    assert metadata["size"] == len(b"second")
    assert metadata["checksum"]["value"] == hashlib.sha256(b"second").hexdigest()
    assert metadata["overwritten"] is True


def test_ingest_refused_overwrite_keeps_original_metadata(tmp_path):
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
    rejected = runner.invoke(main, ["ingest", "episode", str(second), "--archive", str(root)])

    assert rejected.exit_code == 1
    metadata = capture_metadata(root, "capture.txt")
    assert metadata["checksum"]["value"] == hashlib.sha256(b"first").hexdigest()
    assert (root / "inbox" / "capture.txt").read_text(encoding="utf-8") == "first"


def test_ingest_json_output_reports_capture_metadata(tmp_path):
    root = make_archive(tmp_path)
    source = tmp_path / "capture.txt"
    source.write_text("synthetic", encoding="utf-8")

    result = CliRunner().invoke(
        main, ["ingest", "episode", str(source), "--archive", str(root), "--json"]
    )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["filename"] == "capture.txt"
    assert payload["path"] == str(root / "inbox" / "capture.txt")
    assert payload["metadata_path"] == str(root / "inbox" / ".storygram" / "capture.txt.json")
    assert payload["checksum"]["value"] == hashlib.sha256(b"synthetic").hexdigest()
