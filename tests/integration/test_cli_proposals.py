from __future__ import annotations

import json
import subprocess
from pathlib import Path

from click.testing import CliRunner

from storygram.cli import main

NOW = "2026-10-30T12:00:00+00:00"


def proposal(proposal_id: str = "proposal:cli-1") -> dict:
    return {
        "id": proposal_id,
        "type": "Proposal",
        "status": "proposed",
        "created_at": NOW,
        "updated_at": NOW,
        "title": "Add a note episode",
        "operations": [
            {
                "op": "create",
                "record_type": "Episode",
                "record": {
                    "id": "episode:cli-note",
                    "type": "Episode",
                    "episode_type": "other",
                    "status": "reported",
                    "created_at": NOW,
                    "updated_at": NOW,
                },
            }
        ],
    }


def init_archive(tmp_path: Path) -> None:
    result = CliRunner().invoke(main, ["init", str(tmp_path)])
    assert result.exit_code == 0, result.output


def write_proposal(tmp_path: Path, data: dict) -> Path:
    path = tmp_path / "incoming.json"
    path.write_text(json.dumps(data, indent=2))
    return path


def test_init_creates_all_record_directories_and_schemas(tmp_path: Path) -> None:
    init_archive(tmp_path)

    assert (tmp_path / "data" / "proposals").is_dir()
    assert (tmp_path / "data" / "collections").is_dir()
    assert (tmp_path / "proposals").is_dir()
    assert len(list((tmp_path / "schema").glob("*.schema.json"))) == 15


def test_new_list_show_approve_dry_run_and_no_commit(tmp_path: Path, monkeypatch) -> None:
    init_archive(tmp_path)
    monkeypatch.chdir(tmp_path)
    incoming = write_proposal(tmp_path, proposal())
    runner = CliRunner()

    created = runner.invoke(main, ["proposal", "new", "--file", str(incoming)])
    assert created.exit_code == 0, created.output
    listed = runner.invoke(main, ["proposal", "list"])
    assert "proposal:cli-1 [proposed]" in listed.output
    shown = runner.invoke(main, ["proposal", "show", "proposal:cli-1"])
    assert '"id": "proposal:cli-1"' in shown.output

    dry_run = runner.invoke(main, ["proposal", "approve", "proposal:cli-1", "--dry-run"])
    assert dry_run.exit_code == 0, dry_run.output
    assert "DRY RUN" in dry_run.output
    assert not (tmp_path / "data" / "episodes" / "episode_cli-note.json").exists()

    applied = runner.invoke(main, ["proposal", "approve", "proposal:cli-1", "--no-commit"])
    assert applied.exit_code == 0, applied.output
    assert (tmp_path / "data" / "episodes" / "episode_cli-note.json").exists()
    assert (tmp_path / "data" / "proposals" / "proposal_cli-1.json").exists()
    assert not (tmp_path / "proposals" / "proposal_cli-1.json").exists()
    fetched = runner.invoke(main, ["get", "episode:cli-note", "--json"])
    assert fetched.exit_code == 0
    assert json.loads(fetched.output)["id"] == "episode:cli-note"
    valid = runner.invoke(main, ["validate"])
    assert valid.exit_code == 0
    assert valid.output.strip() == "OK"


def test_approve_commits_scoped_changes(tmp_path: Path, monkeypatch) -> None:
    init_archive(tmp_path)
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=tmp_path, check=True)
    subprocess.run(["git", "add", "."], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-qm", "initial"], cwd=tmp_path, check=True)
    monkeypatch.chdir(tmp_path)
    incoming = write_proposal(tmp_path, proposal())
    runner = CliRunner()
    assert runner.invoke(main, ["proposal", "new", "--file", str(incoming)]).exit_code == 0

    result = runner.invoke(main, ["proposal", "approve", "proposal:cli-1"])

    assert result.exit_code == 0, result.output
    assert "Committed" in result.output
    log = subprocess.run(
        ["git", "show", "--name-only", "--format=%s", "HEAD"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    assert "feat(proposal): apply proposal:cli-1" in log
    assert "data/episodes/episode_cli-note.json" in log


def test_reject_marks_pending_proposal(tmp_path: Path, monkeypatch) -> None:
    init_archive(tmp_path)
    monkeypatch.chdir(tmp_path)
    incoming = write_proposal(tmp_path, proposal())
    runner = CliRunner()
    assert runner.invoke(main, ["proposal", "new", "--file", str(incoming)]).exit_code == 0

    rejected = runner.invoke(
        main, ["proposal", "reject", "proposal:cli-1", "--reason", "not enough evidence"]
    )

    assert rejected.exit_code == 0, rejected.output
    data = json.loads((tmp_path / "proposals" / "proposal_cli-1.json").read_text())
    assert data["status"] == "rejected"
    assert data["notes"] == "not enough evidence"


def test_new_rejects_invalid_proposal(tmp_path: Path, monkeypatch) -> None:
    init_archive(tmp_path)
    monkeypatch.chdir(tmp_path)
    incoming = write_proposal(tmp_path, {"id": "proposal:bad", "type": "Proposal"})

    result = CliRunner().invoke(main, ["proposal", "new", "--file", str(incoming)])

    assert result.exit_code != 0
    assert "required property" in result.output


def test_generate_saves_pending_only(tmp_path: Path, monkeypatch) -> None:
    init_archive(tmp_path)
    monkeypatch.chdir(tmp_path)

    def fake_complete(self, prompt: str) -> str:
        return json.dumps(proposal("proposal:generated"))

    monkeypatch.setattr("storygram.llm.OllamaProvider.complete", fake_complete)
    result = CliRunner().invoke(
        main,
        ["proposal", "generate", "--text", "a memory", "--model", "test", "--json"],
    )

    assert result.exit_code == 0, result.output
    output = json.loads(result.output)
    assert output["proposal"]["status"] == "proposed"
    assert output["proposal"]["id"].startswith("proposal:")
    assert Path(output["path"]).exists()
    assert not (tmp_path / "data" / "episodes" / "episode_cli-note.json").exists()


def test_generate_without_save_writes_nothing(tmp_path: Path, monkeypatch) -> None:
    init_archive(tmp_path)
    monkeypatch.chdir(tmp_path)

    def fake_complete(self, prompt: str) -> str:
        return json.dumps(proposal("proposal:generated"))

    monkeypatch.setattr("storygram.llm.OllamaProvider.complete", fake_complete)
    result = CliRunner().invoke(
        main,
        ["proposal", "generate", "--text", "a memory", "--model", "test", "--no-save"],
    )

    assert result.exit_code == 0, result.output
    assert not list((tmp_path / "proposals").glob("*.json"))


def test_init_uses_configured_schema_dir(tmp_path: Path, monkeypatch) -> None:
    archive = tmp_path / "archive"
    monkeypatch.setenv("STORYGRAM_SCHEMA_DIR", str(Path("schema").resolve()))
    result = CliRunner().invoke(main, ["init", str(archive)])

    assert result.exit_code == 0, result.output
    assert (archive / "schema" / "proposal.schema.json").exists()
    assert len(list((archive / "schema").glob("*.schema.json"))) == 15


def test_withdraw_marks_pending_proposal(tmp_path: Path, monkeypatch) -> None:
    init_archive(tmp_path)
    monkeypatch.chdir(tmp_path)
    incoming = write_proposal(tmp_path, proposal())
    runner = CliRunner()
    assert runner.invoke(main, ["proposal", "new", "--file", str(incoming)]).exit_code == 0

    withdrawn = runner.invoke(
        main, ["proposal", "withdraw", "proposal:cli-1", "--reason", "wrong source"]
    )

    assert withdrawn.exit_code == 0, withdrawn.output
    data = json.loads((tmp_path / "proposals" / "proposal_cli-1.json").read_text())
    assert data["status"] == "withdrawn"
    assert data["notes"] == "wrong source"


def test_proposal_show_json_for_agents(tmp_path: Path, monkeypatch) -> None:
    init_archive(tmp_path)
    monkeypatch.chdir(tmp_path)
    incoming = write_proposal(tmp_path, proposal())
    runner = CliRunner()

    created = runner.invoke(main, ["proposal", "new", "--file", str(incoming)])
    assert created.exit_code == 0, created.output

    shown = runner.invoke(main, ["proposal", "show", "proposal:cli-1", "--json"])
    assert shown.exit_code == 0, shown.output
    payload = json.loads(shown.output)
    assert payload["id"] == "proposal:cli-1"
    assert payload["operations"][0]["record"]["id"] == "episode:cli-note"

    missing = runner.invoke(main, ["proposal", "show", "proposal:nope", "--json"])
    assert missing.exit_code == 1
    error = json.loads(missing.output)
    assert error["ok"] is False
    assert "Proposal not found" in error["errors"][0]

    missing_plain = runner.invoke(main, ["proposal", "show", "proposal:nope"])
    assert missing_plain.exit_code == 1
    assert "Proposal not found" in missing_plain.output
