from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest
from click.testing import CliRunner

from storygram.cli import main
from storygram.media import MediaError, add_media, list_media


def init_archive(tmp_path: Path) -> None:
    result = CliRunner().invoke(main, ["init", str(tmp_path)])
    assert result.exit_code == 0, result.output


def test_add_media_writes_checksummed_manifest_without_touching_data(tmp_path: Path) -> None:
    init_archive(tmp_path)
    media_file = tmp_path / "photos" / "portrait.jpg"
    media_file.parent.mkdir(parents=True)
    media_file.write_bytes(b"synthetic-image-bytes")

    entry = add_media(
        tmp_path,
        media_file,
        visibility="family",
        acquired_at="1987",
        notes="Synthetic fixture photo.",
        now="2026-11-04T12:00:00+00:00",
    )

    expected = hashlib.sha256(b"synthetic-image-bytes").hexdigest()
    assert entry["format"] == "storygram.media-manifest/1"
    assert entry["filename"] == "portrait.jpg"
    assert entry["uri"].endswith("photos/portrait.jpg")
    assert entry["checksum"] == {"algorithm": "sha256", "value": expected}
    assert entry["size"] == len(b"synthetic-image-bytes")
    assert entry["mime_type"] == "image/jpeg"
    assert entry["visibility"] == "family"
    assert entry["acquired_at"] == "1987"
    assert entry["notes"] == "Synthetic fixture photo."
    assert entry["registered_at"] == "2026-11-04T12:00:00+00:00"
    assert entry["id"].startswith("media-manifest/portrait-")

    manifest_path = tmp_path / "media-manifest" / f"{entry['id'].split('/', 1)[1]}.json"
    assert manifest_path.exists()
    stored = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert stored == entry

    canonical_files = [
        path
        for path in (tmp_path / "data").rglob("*.json")
        if path.relative_to(tmp_path / "data").parts[0] != "proposals"
    ]
    assert canonical_files == []
    assert list_media(tmp_path) == [entry]


def test_media_cli_add_list_and_overwrite(tmp_path: Path, monkeypatch) -> None:
    init_archive(tmp_path)
    monkeypatch.chdir(tmp_path)
    first = tmp_path / "audio-note.txt"
    first.write_text("first capture", encoding="utf-8")
    second = tmp_path / "second-note.txt"
    second.write_text("second capture", encoding="utf-8")
    runner = CliRunner()

    added = runner.invoke(
        main,
        [
            "media",
            "add",
            str(first),
            "--visibility",
            "private",
            "--notes",
            "voice memo",
            "--json",
        ],
    )
    assert added.exit_code == 0, added.output
    entry = json.loads(added.output)
    assert entry["visibility"] == "private"
    assert entry["notes"] == "voice memo"

    added_two = runner.invoke(main, ["media", "add", str(second)])
    assert added_two.exit_code == 0, added_two.output

    listed = runner.invoke(main, ["media", "list", "--json"])
    assert listed.exit_code == 0, listed.output
    entries = json.loads(listed.output)
    assert len(entries) == 2
    assert [item["id"] for item in entries] == sorted(item["id"] for item in entries)

    plain = runner.invoke(main, ["media", "list"])
    assert plain.exit_code == 0, plain.output
    assert entry["id"] in plain.output
    assert entry["checksum"]["value"][:12] in plain.output

    duplicate = runner.invoke(main, ["media", "add", str(first)])
    assert duplicate.exit_code == 1
    assert "already exists" in duplicate.output

    duplicate_json = runner.invoke(main, ["media", "add", str(first), "--json"])
    assert duplicate_json.exit_code == 1
    error = json.loads(duplicate_json.output)
    assert error["ok"] is False
    assert "already exists" in error["errors"][0]

    refreshed = runner.invoke(
        main,
        ["media", "add", str(first), "--overwrite", "--notes", "refreshed", "--json"],
    )
    assert refreshed.exit_code == 0, refreshed.output
    refreshed_entry = json.loads(refreshed.output)
    assert refreshed_entry["notes"] == "refreshed"
    assert refreshed_entry["checksum"]["value"] == entry["checksum"]["value"]
    assert len(list_media(tmp_path)) == 2


def test_media_cli_errors(tmp_path: Path, monkeypatch) -> None:
    init_archive(tmp_path)
    monkeypatch.chdir(tmp_path)
    runner = CliRunner()

    missing = runner.invoke(main, ["media", "add", str(tmp_path / "absent.jpg")])
    assert missing.exit_code != 0

    existing = tmp_path / "note.txt"
    existing.write_text("x", encoding="utf-8")
    bad_visibility = runner.invoke(main, ["media", "add", str(existing), "--visibility", "secret"])
    assert bad_visibility.exit_code != 0
    assert "Invalid value for '--visibility'" in bad_visibility.output

    empty = runner.invoke(main, ["media", "list"])
    assert empty.exit_code == 0, empty.output
    assert "No media registered." in empty.output

    with pytest.raises(MediaError, match="not found"):
        add_media(tmp_path, tmp_path / "absent.jpg")
    with pytest.raises(MediaError, match="unsupported visibility"):
        add_media(tmp_path, __file__, visibility="secret")
