import json
import shutil
from pathlib import Path

import pytest
from click.testing import CliRunner

from storygram.cli import main
from storygram.export import export_json, export_jsonld, export_markdown, export_yaml

NOW = "2026-11-03T10:00:00+00:00"

EPISODE = {
    "id": "episode:garden",
    "type": "Episode",
    "episode_type": "memory",
    "status": "reported",
    "created_at": NOW,
    "updated_at": NOW,
    "content": {"text": "A synthetic memory about the garden.", "mime_type": "text/plain"},
    "captured_at": "1987",
    "visibility": "public",
}

SOURCE = {
    "id": "source:register",
    "type": "Source",
    "title": "Synthetic family register",
    "source_type": "registry",
    "status": "reported",
    "created_at": NOW,
    "updated_at": NOW,
    "visibility": "family",
}

PERSON = {
    "id": "person:maria",
    "type": "Person",
    "name": "Maria",
    "status": "reported",
    "created_at": NOW,
    "updated_at": NOW,
    "visibility": "family",
    "notes": "Synthetic fixture person.",
}


def make_archive(root: Path) -> Path:
    shutil.copytree(Path("schema"), root / "schema")
    for directory in ("episodes", "people", "assertions", "places", "sources"):
        (root / "data" / directory).mkdir(parents=True, exist_ok=True)
    (root / "data" / "proposals").mkdir(parents=True, exist_ok=True)
    (root / "proposals").mkdir()
    return root


def write_record(root: Path, record: dict) -> Path:
    directories = {
        "Episode": "episodes",
        "Person": "people",
        "Assertion": "assertions",
        "Place": "places",
        "Source": "sources",
    }
    path = root / "data" / directories[record["type"]] / (record["id"].replace(":", "_") + ".json")
    path.write_text(json.dumps(record), encoding="utf-8")
    return path


def pending_files(root: Path) -> list[Path]:
    return sorted(path for path in (root / "proposals").glob("*.json"))


def test_import_creates_pending_only_and_approval_writes_canonical(tmp_path):
    target = make_archive(tmp_path / "target")
    write_record(target, EPISODE)
    source = make_archive(tmp_path / "source")
    write_record(source, PERSON)
    export_file = tmp_path / "person.yaml"
    export_file.write_text(export_yaml(source), encoding="utf-8")
    runner = CliRunner()

    imported = runner.invoke(
        main,
        [
            "import",
            str(export_file),
            "--archive",
            str(target),
            "--id",
            "proposal:import-person",
            "--evidence",
            "episode:garden",
            "--json",
        ],
    )

    assert imported.exit_code == 0, imported.output
    result = json.loads(imported.output)
    assert result["proposal_id"] == "proposal:import-person"
    assert result["records"] == 1
    assert result["operations"][0]["evidence"] == ["episode:garden"]
    assert not (target / "data" / "people" / "person_maria.json").exists()
    assert len(pending_files(target)) == 1

    approved = runner.invoke(
        main,
        [
            "proposal",
            "approve",
            "proposal:import-person",
            "--archive",
            str(target),
            "--no-commit",
            "--json",
        ],
    )

    assert approved.exit_code == 0, approved.output
    assert (target / "data" / "people" / "person_maria.json").exists()
    assert pending_files(target) == []


@pytest.mark.parametrize(
    ("suffix", "serialize"),
    [
        (".json", lambda root: json.dumps(export_json(root))),
        (".jsonld", lambda root: json.dumps(export_jsonld(root))),
        (".yaml", export_yaml),
        (".md", export_markdown),
    ],
)
def test_import_detects_each_export_format(tmp_path, suffix, serialize):
    target = make_archive(tmp_path / "target")
    source = make_archive(tmp_path / "source")
    write_record(source, EPISODE)
    export_file = tmp_path / f"episode{suffix}"
    export_file.write_text(serialize(source), encoding="utf-8")

    result = CliRunner().invoke(
        main,
        ["import", str(export_file), "--archive", str(target), "--id", "proposal:import-episode"],
    )

    assert result.exit_code == 0, result.output
    assert not (target / "data" / "episodes" / "episode_garden.json").exists()
    assert len(pending_files(target)) == 1


def test_import_wires_imported_episode_as_evidence(tmp_path):
    target = make_archive(tmp_path / "target")
    source = make_archive(tmp_path / "source")
    write_record(source, EPISODE)
    write_record(source, PERSON)
    export_file = tmp_path / "records.yaml"
    export_file.write_text(export_yaml(source), encoding="utf-8")
    runner = CliRunner()

    result = runner.invoke(
        main,
        ["import", str(export_file), "--archive", str(target), "--id", "proposal:import-batch"],
    )

    assert result.exit_code == 0, result.output
    proposal = json.loads(
        (target / "proposals" / "proposal_import-batch.json").read_text(encoding="utf-8")
    )
    assert [operation["record_type"] for operation in proposal["operations"]] == [
        "Episode",
        "Person",
    ]
    assert "evidence" not in proposal["operations"][0]
    assert proposal["operations"][1]["evidence"] == ["episode:garden"]

    approved = runner.invoke(
        main,
        [
            "proposal",
            "approve",
            "proposal:import-batch",
            "--archive",
            str(target),
            "--no-commit",
            "--json",
        ],
    )

    assert approved.exit_code == 0, approved.output
    assert (target / "data" / "episodes" / "episode_garden.json").exists()
    assert (target / "data" / "people" / "person_maria.json").exists()


def test_import_rejects_missing_evidence_without_writing(tmp_path):
    target = make_archive(tmp_path / "target")
    source = make_archive(tmp_path / "source")
    write_record(source, PERSON)
    export_file = tmp_path / "person.yaml"
    export_file.write_text(export_yaml(source), encoding="utf-8")

    result = CliRunner().invoke(main, ["import", str(export_file), "--archive", str(target)])

    assert result.exit_code == 1
    assert "evidence is required" in result.output
    assert pending_files(target) == []
    assert not (target / "data" / "people" / "person_maria.json").exists()


def test_import_rejects_invalid_record_without_writing(tmp_path):
    target = make_archive(tmp_path / "target")
    export_file = tmp_path / "bad.yaml"
    export_file.write_text(
        "- id: person:bad\n  type: Person\n  name: Bad\n",
        encoding="utf-8",
    )

    result = CliRunner().invoke(main, ["import", str(export_file), "--archive", str(target)])

    assert result.exit_code == 1
    assert "schema validation error" in result.output
    assert pending_files(target) == []


def test_import_rejects_duplicate_ids_in_export(tmp_path):
    target = make_archive(tmp_path / "target")
    export_file = tmp_path / "duplicate.yaml"
    export_file.write_text(
        "- id: episode:garden\n"
        "  type: Episode\n"
        "  episode_type: memory\n"
        "  status: reported\n"
        f"  created_at: '{NOW}'\n"
        f"  updated_at: '{NOW}'\n"
        "- id: episode:garden\n"
        "  type: Episode\n"
        "  episode_type: memory\n"
        "  status: reported\n"
        f"  created_at: '{NOW}'\n"
        f"  updated_at: '{NOW}'\n",
        encoding="utf-8",
    )

    result = CliRunner().invoke(main, ["import", str(export_file), "--archive", str(target)])

    assert result.exit_code == 1
    assert "duplicate id" in result.output
    assert pending_files(target) == []


def test_import_rejects_record_id_already_in_canonical_data(tmp_path):
    target = make_archive(tmp_path / "target")
    write_record(target, EPISODE)
    write_record(target, PERSON)
    source = make_archive(tmp_path / "source")
    write_record(source, PERSON)
    export_file = tmp_path / "person.yaml"
    export_file.write_text(export_yaml(source), encoding="utf-8")

    result = CliRunner().invoke(
        main,
        [
            "import",
            str(export_file),
            "--archive",
            str(target),
            "--evidence",
            "episode:garden",
        ],
    )

    assert result.exit_code == 1
    assert "id already exists" in result.output
    assert pending_files(target) == []


def test_import_requires_known_format_or_explicit_override(tmp_path):
    target = make_archive(tmp_path / "target")
    source = make_archive(tmp_path / "source")
    write_record(source, EPISODE)
    export_file = tmp_path / "episode.txt"
    export_file.write_text(export_yaml(source), encoding="utf-8")
    runner = CliRunner()

    rejected = runner.invoke(main, ["import", str(export_file), "--archive", str(target)])
    accepted = runner.invoke(
        main,
        [
            "import",
            str(export_file),
            "--archive",
            str(target),
            "--format",
            "yaml",
            "--id",
            "proposal:import-text",
        ],
    )

    assert rejected.exit_code == 1
    assert "use --format" in rejected.output
    assert accepted.exit_code == 0, accepted.output


def test_import_standalone_source_does_not_require_evidence(tmp_path):
    target = make_archive(tmp_path / "target")
    source = make_archive(tmp_path / "source")
    write_record(source, SOURCE)
    export_file = tmp_path / "source.json"
    export_file.write_text(json.dumps(export_json(source)), encoding="utf-8")
    runner = CliRunner()

    imported = runner.invoke(
        main,
        [
            "import",
            str(export_file),
            "--archive",
            str(target),
            "--id",
            "proposal:import-source",
            "--json",
        ],
    )

    assert imported.exit_code == 0, imported.output
    result = json.loads(imported.output)
    assert result["operations"][0].get("evidence", []) == []
    assert len(pending_files(target)) == 1

    approved = runner.invoke(
        main,
        [
            "proposal",
            "approve",
            "proposal:import-source",
            "--archive",
            str(target),
            "--no-commit",
            "--json",
        ],
    )

    assert approved.exit_code == 0, approved.output
    assert (target / "data" / "sources" / "source_register.json").exists()
