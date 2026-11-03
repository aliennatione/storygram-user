import json
from pathlib import Path

from click.testing import CliRunner

from storygram.cli import main
from storygram.export import (
    ExportError,
    export_jsonld,
    export_markdown,
    export_yaml,
    records_from_jsonld,
    records_from_markdown,
    records_from_yaml,
)


def make_archive(tmp_path: Path) -> Path:
    (tmp_path / "data" / "people").mkdir(parents=True)
    (tmp_path / "data" / "episodes").mkdir(parents=True)
    (tmp_path / "data" / "assertions").mkdir(parents=True)
    return tmp_path


def write(root: Path, relative: str, data: dict) -> None:
    path = root / "data" / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data), encoding="utf-8")


PERSON = {
    "id": "person:maria",
    "type": "Person",
    "name": "Maria",
    "status": "confirmed",
    "created_at": "2026-11-02T10:00:00+00:00",
    "updated_at": "2026-11-02T10:00:00+00:00",
    "visibility": "family",
    "tags": ["synthetic"],
    "notes": "Synthetic fixture person.",
}

EPISODE = {
    "id": "episode:garden",
    "type": "Episode",
    "episode_type": "memory",
    "status": "reported",
    "created_at": "2026-11-02T10:00:00+00:00",
    "updated_at": "2026-11-02T10:00:00+00:00",
    "content": {"text": "A synthetic memory about the garden.", "mime_type": "text/plain"},
    "captured_at": "1987",
    "visibility": "public",
}

ASSERTION = {
    "id": "assertion:garden",
    "type": "Assertion",
    "subject": "person:maria",
    "predicate": "relation:lived_in",
    "object": "place:torino",
    "status": "reported",
    "transaction_time": {"recorded_at": "2026-11-02T10:00:00+00:00"},
    "valid_time": {"start": "1987", "end": "1995", "precision": "year"},
    "created_at": "2026-11-02T10:00:00+00:00",
    "updated_at": "2026-11-02T10:00:00+00:00",
    "visibility": "family",
}


def test_yaml_roundtrip_single_record(tmp_path):
    root = make_archive(tmp_path)
    write(root, "people/maria.json", PERSON)

    exported = export_yaml(root)

    assert records_from_yaml(exported) == [PERSON]


def test_yaml_roundtrip_keeps_nested_values(tmp_path):
    root = make_archive(tmp_path)
    write(root, "assertions/garden.json", ASSERTION)

    assert records_from_yaml(export_yaml(root)) == [ASSERTION]


def test_jsonld_roundtrip_single_record(tmp_path):
    root = make_archive(tmp_path)
    write(root, "people/maria.json", PERSON)

    exported = export_jsonld(root)

    assert records_from_jsonld(exported) == [PERSON]


def test_jsonld_roundtrip_keeps_nested_values(tmp_path):
    root = make_archive(tmp_path)
    write(root, "assertions/garden.json", ASSERTION)

    assert records_from_jsonld(export_jsonld(root)) == [ASSERTION]


def test_markdown_roundtrip_moves_episode_text_to_body(tmp_path):
    root = make_archive(tmp_path)
    write(root, "episodes/garden.json", EPISODE)

    exported = export_markdown(root)

    assert "A synthetic memory about the garden." in exported
    assert "text:" not in exported
    assert records_from_markdown(exported) == [EPISODE]


def test_markdown_roundtrip_keeps_notes_in_body(tmp_path):
    root = make_archive(tmp_path)
    write(root, "people/maria.json", PERSON)

    exported = export_markdown(root)

    assert "Synthetic fixture person." in exported
    assert records_from_markdown(exported) == [PERSON]


def test_markdown_roundtrip_multiple_records(tmp_path):
    root = make_archive(tmp_path)
    write(root, "people/maria.json", PERSON)
    write(root, "episodes/garden.json", EPISODE)

    assert records_from_markdown(export_markdown(root)) == [EPISODE, PERSON]


def test_markdown_roundtrip_keeps_body_trailing_newlines(tmp_path):
    root = make_archive(tmp_path)
    episode = {**EPISODE, "content": {"text": "Line one.\nLine two.\n"}}
    write(root, "episodes/garden.json", episode)

    assert records_from_markdown(export_markdown(root)) == [episode]


def test_yaml_parser_reports_wrong_shape():
    try:
        records_from_yaml("- not a record")
    except ExportError as exc:
        assert "object" in str(exc)
    else:
        raise AssertionError("non-object YAML records must fail")


def test_jsonld_parser_reports_missing_graph():
    try:
        records_from_jsonld({"@context": {}})
    except ExportError as exc:
        assert "@graph" in str(exc)
    else:
        raise AssertionError("JSON-LD without a graph must fail")


def test_markdown_parser_reports_missing_front_matter():
    try:
        records_from_markdown("<!-- storygram:record -->\nno front matter\n")
    except ExportError as exc:
        assert "front matter" in str(exc)
    else:
        raise AssertionError("Markdown without front matter must fail")


def test_export_cli_emits_yaml_that_parses_back(tmp_path):
    root = make_archive(tmp_path)
    write(root, "people/maria.json", PERSON)

    result = CliRunner().invoke(main, ["export", "--archive", str(root), "--format", "yaml"])

    assert result.exit_code == 0, result.output
    assert records_from_yaml(result.output) == [PERSON]


def test_export_cli_emits_markdown_that_parses_back(tmp_path):
    root = make_archive(tmp_path)
    write(root, "episodes/garden.json", EPISODE)

    result = CliRunner().invoke(main, ["export", "--archive", str(root), "--format", "markdown"])

    assert result.exit_code == 0, result.output
    assert records_from_markdown(result.output) == [EPISODE]
