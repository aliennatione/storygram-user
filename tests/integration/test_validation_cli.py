import tempfile
from pathlib import Path

from storygram import validate
from storygram.models import Relationship
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


def test_relationship_temporal_fields_are_optional_and_validated(tmp_path: Path):
    record_type = TYPE_BY_NAME["Relationship"]
    base = {
        "id": "relationship:anna-parent",
        "type": "Relationship",
        "subject": "person:anna",
        "predicate": "relation:parent",
        "object": "person:bruno",
        "status": "reported",
        "created_at": "2026-01-01T00:00:00+00:00",
        "updated_at": "2026-01-01T00:00:00+00:00",
    }
    with_times = {
        **base,
        "valid_time": {"start": "1987", "end": "1995", "precision": "year"},
        "transaction_time": {
            "recorded_at": "2026-01-01T00:00:00+00:00",
            "recorded_until": None,
        },
    }
    missing_recorded_at = {**base, "transaction_time": {"recorded_until": None}}
    invalid_precision = {**base, "valid_time": {"start": "1987", "precision": "century"}}

    assert validate.validate_instance(tmp_path, base, record_type) == []
    assert validate.validate_instance(tmp_path, with_times, record_type) == []
    assert validate.validate_instance(tmp_path, missing_recorded_at, record_type)
    assert validate.validate_instance(tmp_path, invalid_precision, record_type)


def test_relationship_model_accepts_temporal_fields():
    record = Relationship.model_validate(
        {
            "id": "relationship:anna-parent",
            "type": "Relationship",
            "subject": "person:anna",
            "predicate": "relation:parent",
            "object": "person:bruno",
            "valid_time": {"start": "1987", "end": "1995", "precision": "year"},
            "transaction_time": {
                "recorded_at": "2026-01-01T00:00:00+00:00",
                "recorded_until": None,
            },
            "status": "reported",
            "created_at": "2026-01-01T00:00:00+00:00",
            "updated_at": "2026-01-01T00:00:00+00:00",
        }
    )

    assert record.valid_time is not None
    assert record.valid_time.start == "1987"
    assert record.transaction_time is not None
    assert record.transaction_time.recorded_at.isoformat() == "2026-01-01T00:00:00+00:00"
