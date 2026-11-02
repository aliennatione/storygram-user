from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest

from storygram.proposals import ProposalError, apply_proposal, plan_apply, reject_proposal

NOW = "2026-01-01T00:00:00+00:00"
EVIDENCE = "episode:evidence-1"


def make_archive(tmp_path: Path) -> Path:
    shutil.copytree(Path("schema"), tmp_path / "schema")
    for directory in ("episodes", "assertions", "people", "places", "conflicts", "proposals"):
        (tmp_path / "data" / directory).mkdir(parents=True, exist_ok=True)
    (tmp_path / "proposals").mkdir()
    return tmp_path


def write_record(root: Path, record: dict) -> Path:
    mapping = {
        "Episode": "episodes",
        "Assertion": "assertions",
        "Person": "people",
        "Place": "places",
        "Conflict": "conflicts",
    }
    path = root / "data" / mapping[record["type"]] / (record["id"].replace(":", "_") + ".json")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(record, indent=2) + "\n")
    return path


def base_record(record_id: str, record_type: str, **extra: object) -> dict:
    record = {
        "id": record_id,
        "type": record_type,
        "status": "reported",
        "created_at": NOW,
        "updated_at": NOW,
    }
    record.update(extra)
    return record


def episode() -> dict:
    return base_record(EVIDENCE, "Episode", episode_type="interview")


def person() -> dict:
    return base_record("person:p1", "Person")


def place(record_id: str = "place:home") -> dict:
    return base_record(record_id, "Place")


def assertion(record_id: str, target: str, **extra: object) -> dict:
    record = base_record(
        record_id,
        "Assertion",
        subject="person:p1",
        predicate="relation:lives_in",
        object=target,
        transaction_time={"recorded_at": NOW},
        valid_time={"start": "1980", "end": "1990", "precision": "year"},
    )
    record.update(extra)
    return record


def proposal(
    *operations: dict, proposal_id: str = "proposal:p1", evidence: list[str] | None = None
) -> dict:
    return {
        "id": proposal_id,
        "type": "Proposal",
        "status": "proposed",
        "created_at": NOW,
        "updated_at": NOW,
        "evidence": evidence or [],
        "operations": list(operations),
    }


def save_proposal(root: Path, data: dict) -> Path:
    path = root / "proposals" / (str(data["id"]).replace(":", "_") + ".json")
    path.write_text(json.dumps(data, indent=2) + "\n")
    return path


def test_dry_run_does_not_write_or_archive(tmp_path: Path) -> None:
    root = make_archive(tmp_path)
    save_proposal(
        root,
        proposal(
            {
                "op": "create",
                "record_type": "Episode",
                "record": base_record("episode:new", "Episode", episode_type="other"),
            }
        ),
    )

    result = apply_proposal(root, "proposal:p1", dry_run=True)

    assert result["dry_run"] is True
    assert result["files"] == ["data/episodes/episode_new.json", "data/proposals/proposal_p1.json"]
    assert not (root / "data" / "episodes" / "episode_new.json").exists()
    assert (root / "proposals" / "proposal_p1.json").exists()


def test_dry_run_reports_record_type_mismatch_without_crashing(tmp_path: Path) -> None:
    root = make_archive(tmp_path)
    record = base_record("person:p2", "Person")
    record["type"] = "sibling"
    save_proposal(
        root,
        proposal({"op": "create", "record_type": "Person", "record": record}),
    )

    with pytest.raises(ProposalError, match="record type must be Person"):
        apply_proposal(root, "proposal:p1", dry_run=True)


def test_apply_creates_record_archives_proposal_and_removes_pending(tmp_path: Path) -> None:
    root = make_archive(tmp_path)
    save_proposal(
        root,
        proposal(
            {
                "op": "create",
                "record_type": "Episode",
                "record": base_record("episode:new", "Episode", episode_type="other"),
            }
        ),
    )

    result = apply_proposal(root, "proposal:p1", commit=False, now=NOW)

    assert result["commit"] is None
    assert (
        json.loads((root / "data" / "episodes" / "episode_new.json").read_text())["id"]
        == "episode:new"
    )
    archived = json.loads((root / "data" / "proposals" / "proposal_p1.json").read_text())
    assert archived["status"] == "merged"
    assert archived["applied_at"] == NOW
    assert not (root / "proposals" / "proposal_p1.json").exists()


def test_metadata_policy_rejects_factual_field(tmp_path: Path) -> None:
    root = make_archive(tmp_path)
    write_record(root, episode())
    save_proposal(
        root,
        proposal(
            {
                "op": "update_metadata",
                "record_type": "Episode",
                "target_id": EVIDENCE,
                "fields": {"episode_type": "interview"},
            }
        ),
    )

    with pytest.raises(ProposalError, match="fields not allowed"):
        plan_apply(
            root,
            proposal(
                {
                    "op": "update_metadata",
                    "record_type": "Episode",
                    "target_id": EVIDENCE,
                    "fields": {"episode_type": "interview"},
                }
            ),
        )


def test_metadata_policy_allows_admin_fields(tmp_path: Path) -> None:
    root = make_archive(tmp_path)
    write_record(root, episode())
    data = proposal(
        {
            "op": "update_metadata",
            "record_type": "Episode",
            "target_id": EVIDENCE,
            "fields": {"tags": ["childhood"], "visibility": "family"},
        }
    )
    save_proposal(root, data)

    apply_proposal(root, "proposal:p1", commit=False, now=NOW)

    updated = json.loads((root / "data" / "episodes" / "episode_evidence-1.json").read_text())
    assert updated["tags"] == ["childhood"]
    assert updated["visibility"] == "family"


def test_assertion_supersession_closes_transaction_time(tmp_path: Path) -> None:
    root = make_archive(tmp_path)
    write_record(root, episode())
    write_record(root, person())
    write_record(root, place("place:old"))
    write_record(root, place("place:new"))
    write_record(root, assertion("assertion:old", "place:old"))
    replacement = assertion(
        "assertion:new",
        "place:new",
        supersedes=["assertion:old"],
        transaction_time={"recorded_at": "2026-02-01T00:00:00+00:00"},
    )
    data = proposal(
        {
            "op": "supersede",
            "record_type": "Assertion",
            "target_id": "assertion:old",
            "record": replacement,
        },
        evidence=[EVIDENCE],
    )
    save_proposal(root, data)

    apply_proposal(root, "proposal:p1", commit=False, now=NOW)

    old = json.loads((root / "data" / "assertions" / "assertion_old.json").read_text())
    new = json.loads((root / "data" / "assertions" / "assertion_new.json").read_text())
    assert old["status"] == "superseded"
    assert old["transaction_time"]["recorded_until"] == "2026-02-01T00:00:00+00:00"
    assert new["supersedes"] == ["assertion:old"]


def test_unmodelled_conflict_blocks_apply(tmp_path: Path) -> None:
    root = make_archive(tmp_path)
    write_record(root, episode())
    write_record(root, person())
    write_record(root, place("place:a"))
    write_record(root, place("place:b"))
    write_record(root, assertion("assertion:existing", "place:a"))
    create = assertion("assertion:new", "place:b")
    data = proposal(
        {"op": "create", "record_type": "Assertion", "record": create},
        evidence=[EVIDENCE],
    )

    with pytest.raises(ProposalError, match="unmodelled conflict"):
        plan_apply(root, data)


def test_explicit_conflict_allows_apply(tmp_path: Path) -> None:
    root = make_archive(tmp_path)
    write_record(root, episode())
    write_record(root, person())
    write_record(root, place("place:a"))
    write_record(root, place("place:b"))
    write_record(root, assertion("assertion:existing", "place:a"))
    create = assertion("assertion:new", "place:b")
    conflict = base_record(
        "conflict:c1",
        "Conflict",
        assertions=["assertion:existing", "assertion:new"],
        status="open",
    )
    data = proposal(
        {"op": "create", "record_type": "Assertion", "record": create},
        {"op": "create", "record_type": "Conflict", "record": conflict},
        evidence=[EVIDENCE],
    )
    save_proposal(root, data)

    apply_proposal(root, "proposal:p1", commit=False)

    assert (root / "data" / "assertions" / "assertion_new.json").exists()
    assert (root / "data" / "conflicts" / "conflict_c1.json").exists()


def test_evidence_is_required_for_semantic_assertion(tmp_path: Path) -> None:
    root = make_archive(tmp_path)
    write_record(root, person())
    write_record(root, place())
    data = proposal(
        {
            "op": "create",
            "record_type": "Assertion",
            "record": assertion("assertion:new", "place:home"),
        }
    )

    with pytest.raises(ProposalError, match="evidence is required"):
        plan_apply(root, data)


def test_conflict_cannot_be_archived(tmp_path: Path) -> None:
    root = make_archive(tmp_path)
    write_record(
        root,
        base_record(
            "conflict:c1",
            "Conflict",
            assertions=["assertion:a", "assertion:b"],
            status="open",
        ),
    )
    data = proposal(
        {"op": "archive", "record_type": "Conflict", "target_id": "conflict:c1"},
        evidence=[EVIDENCE],
    )

    with pytest.raises(ProposalError, match="cannot be archived"):
        plan_apply(root, data)


def init_git(root: Path) -> None:
    subprocess.run(["git", "init", "-q"], cwd=root, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=root, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=root, check=True)
    subprocess.run(["git", "add", "."], cwd=root, check=True)
    subprocess.run(["git", "commit", "-qm", "initial"], cwd=root, check=True)


def test_apply_commits_only_application_files(tmp_path: Path) -> None:
    root = make_archive(tmp_path)
    init_git(root)
    save_proposal(
        root,
        proposal(
            {
                "op": "create",
                "record_type": "Episode",
                "record": base_record("episode:new", "Episode", episode_type="other"),
            }
        ),
    )

    result = apply_proposal(root, "proposal:p1")

    assert result["commit"]
    log = subprocess.run(
        ["git", "show", "--name-only", "--format=%s", "HEAD"],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    assert "feat(proposal): apply proposal:p1" in log
    assert "data/episodes/episode_new.json" in log
    assert "data/proposals/proposal_p1.json" in log


def test_dirty_tracked_tree_blocks_apply(tmp_path: Path) -> None:
    root = make_archive(tmp_path)
    episode_path = write_record(root, episode())
    init_git(root)
    episode_path.write_text(episode_path.read_text() + "\n")
    save_proposal(
        root,
        proposal(
            {
                "op": "create",
                "record_type": "Episode",
                "record": base_record("episode:new", "Episode", episode_type="other"),
            }
        ),
    )

    with pytest.raises(ProposalError, match="uncommitted tracked changes"):
        apply_proposal(root, "proposal:p1")

    assert not (root / "data" / "episodes" / "episode_new.json").exists()


def test_reject_pending_proposal(tmp_path: Path) -> None:
    root = make_archive(tmp_path)
    save_proposal(
        root,
        proposal(
            {
                "op": "create",
                "record_type": "Episode",
                "record": base_record("episode:new", "Episode", episode_type="other"),
            }
        ),
    )

    reject_proposal(root, "proposal:p1", reason="not enough evidence", now=NOW)

    rejected = json.loads((root / "proposals" / "proposal_p1.json").read_text())
    assert rejected["status"] == "rejected"
    assert rejected["notes"] == "not enough evidence"
