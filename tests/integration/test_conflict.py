import json
from pathlib import Path

from jsonschema import validate


def test_conflicting_assertions_represented():
    as_schema = json.loads(Path("schema/assertion.schema.json").read_text())

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
        "confidence": "low",
        "valid_time": {"start": "1987", "end": "1990", "precision": "year"},
        "transaction_time": {"recorded_at": "2026-05-01T10:00:00+01:00", "recorded_until": None},
        "produced_by": ["episode:interview_02"],
        "supported_by": ["source:interview_transcript_02"],
        "contradicts": ["assertion:01"],
        "created_at": "2026-05-01T10:00:00+01:00",
        "updated_at": "2026-05-01T10:00:00+01:00",
        "visibility": "family",
    }
    validate(instance=a2, schema=as_schema)
    assert "assertion:01" in a2["contradicts"]
