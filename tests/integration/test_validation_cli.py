import tempfile
from pathlib import Path

from storygram import validate
from storygram.registry import TYPE_BY_NAME


def test_validate_empty_archive():
    d = Path(tempfile.mkdtemp())
    # create structure
    for sub in ["data/episodes", "data/assertions"]:
        (d / sub).mkdir(parents=True, exist_ok=True)
    res = validate.validate_archive(d)
    assert res["ok"]


def test_relationship_endpoints_are_validated_together(tmp_path: Path):
    record_type = TYPE_BY_NAME["Relationship"]
    complete = {
        "id": "relationship:anna-parent",
        "type": "Relationship",
        "subject": "person:anna",
        "predicate": "relation:parent",
        "object": "person:bruno",
        "status": "reported",
        "created_at": "2026-01-01T00:00:00+00:00",
        "updated_at": "2026-01-01T00:00:00+00:00",
    }
    partial = dict(complete)
    partial.pop("object")

    assert validate.validate_instance(tmp_path, complete, record_type) == []
    assert validate.validate_instance(tmp_path, partial, record_type)
