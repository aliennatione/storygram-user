import json
from pathlib import Path

from jsonschema import validate


def test_conflict_has_both_sides():
    as_schema = json.loads(Path("schema/assertion.schema.json").read_text())
    c_schema = json.loads(Path("schema/conflict.schema.json").read_text())
    a1 = json.loads(Path("tests/fixtures/assertion_lived_in.json").read_text())
    validate(instance=a1, schema=as_schema)
    a2 = {
        "id": "assertion:03",
        "type": "Assertion",
        "subject": "person:mario_rossi",
        "predicate": "relation:lived_in",
        "object": "place:bergamo",
        "status": "reported",
        "certainty": "reported",
        "valid_time": {"start": "1987", "end": "1990", "precision": "year"},
        "transaction_time": {"recorded_at": "2026-05-01T10:00:00+01:00", "recorded_until": None},
        "produced_by": ["episode:interview_02"],
        "supported_by": ["source:interview_transcript_02"],
        "contradicts": ["assertion:01"],
        "created_at": "2026-05-01T10:00:00+01:00",
        "updated_at": "2026-05-01T10:00:00+01:00",
    }
    validate(instance=a2, schema=as_schema)
    conflict = {
        "id": "conflict:01",
        "type": "Conflict",
        "assertions": ["assertion:01", "assertion:03"],
        "relation": "contradicts",
        "status": "open",
        "reason": "Different locations reported",
        "created_at": "2026-05-01T12:00:00+01:00",
        "updated_at": "2026-05-01T12:00:00+01:00",
    }
    validate(instance=conflict, schema=c_schema)
