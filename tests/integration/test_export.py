import json
from pathlib import Path

from click.testing import CliRunner

from storygram.cli import main
from storygram.export import ExportError, export_json, export_jsonld


def make_archive(tmp_path: Path) -> Path:
    (tmp_path / "data" / "people").mkdir(parents=True)
    (tmp_path / "data" / "conflicts").mkdir(parents=True)
    return tmp_path


def write(root: Path, relative: str, data: dict) -> None:
    path = root / "data" / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data), encoding="utf-8")


def test_export_visibility_filter_is_default_deny(tmp_path):
    root = make_archive(tmp_path)
    write(root, "people/public.json", {"id": "person:public", "type": "Person", "visibility": "public"})
    write(root, "people/private.json", {"id": "person:private", "type": "Person", "visibility": "private"})
    write(root, "conflicts/unclassified.json", {"id": "conflict:01", "type": "Conflict"})

    assert [r["id"] for r in export_json(root, {"public"})] == ["person:public"]
    assert [r["id"] for r in export_json(root)] == [
        "conflict:01",
        "person:private",
        "person:public",
    ]


def test_export_jsonld_marks_each_node(tmp_path):
    root = make_archive(tmp_path)
    write(root, "people/public.json", {"id": "person:public", "type": "Person", "visibility": "public"})

    result = export_jsonld(root, {"public"})

    assert result["@context"]["@vocab"].startswith("https://storygram.local/")
    assert result["@graph"] == [
        {"@id": "person:public", "@type": "Person", "visibility": "public"}
    ]


def test_export_reports_malformed_json(tmp_path):
    root = make_archive(tmp_path)
    (root / "data" / "people" / "broken.json").write_text("{not json", encoding="utf-8")

    try:
        export_json(root)
    except ExportError as exc:
        assert "broken.json" in str(exc)
    else:
        raise AssertionError("malformed JSON must fail the export")


def test_export_cli_filters_and_uses_archive(tmp_path):
    root = make_archive(tmp_path)
    write(root, "people/public.json", {"id": "person:public", "type": "Person", "visibility": "public"})
    write(root, "people/private.json", {"id": "person:private", "type": "Person", "visibility": "private"})

    result = CliRunner().invoke(
        main,
        ["export", "--archive", str(root), "--visibility", "public", "--format", "json"],
    )

    assert result.exit_code == 0, result.output
    assert json.loads(result.output) == [
        {"id": "person:public", "type": "Person", "visibility": "public"}
    ]


def test_export_cli_reports_malformed_json(tmp_path):
    root = make_archive(tmp_path)
    (root / "data" / "people" / "broken.json").write_text("{not json", encoding="utf-8")

    result = CliRunner().invoke(main, ["export", "--archive", str(root)])

    assert result.exit_code == 1
    assert "broken.json" in result.output
