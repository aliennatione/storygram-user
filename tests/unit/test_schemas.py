import json
from pathlib import Path

from jsonschema import ValidationError, validate


def test_episode_schema_valid():
    schema = json.loads(Path("schema/episode.schema.json").read_text())
    instance = {
        "id": "episode:01",
        "type": "Episode",
        "episode_type": "interview",
        "status": "reported",
        "created_at": "2026-10-07T10:00:00+02:00",
        "updated_at": "2026-10-07T10:00:00+02:00",
        "visibility": "family",
    }
    validate(instance=instance, schema=schema)


def test_episode_schema_invalid_missing_required():
    schema = json.loads(Path("schema/episode.schema.json").read_text())
    instance = {"id": "episode:01", "type": "Episode"}
    try:
        validate(instance=instance, schema=schema)
        raise AssertionError("should have failed")
    except ValidationError:
        pass


def test_assertion_schema_valid():
    schema = json.loads(Path("schema/assertion.schema.json").read_text())
    instance = {
        "id": "assertion:01",
        "type": "Assertion",
        "subject": "person:01",
        "predicate": "relation:lived_in",
        "object": "place:01",
        "status": "reported",
        "transaction_time": {"recorded_at": "2026-10-07T10:00:00+02:00", "recorded_until": None},
        "created_at": "2026-10-07T10:00:00+02:00",
        "updated_at": "2026-10-07T10:00:00+02:00",
        "valid_time": {"start": "1987", "end": "1995", "precision": "year"},
    }
    validate(instance=instance, schema=schema)


def test_assertion_superseded_requires_transaction_close():
    schema = json.loads(Path("schema/assertion.schema.json").read_text())
    instance = {
        "id": "assertion:02",
        "type": "Assertion",
        "subject": "person:01",
        "predicate": "relation:lived_in",
        "object": "place:01",
        "status": "superseded",
        "transaction_time": {
            "recorded_at": "2026-10-07T10:00:00+02:00",
            "recorded_until": "2027-03-10T09:15:00+02:00",
        },
        "created_at": "2026-10-07T10:00:00+02:00",
        "updated_at": "2026-10-07T10:00:00+02:00",
    }
    validate(instance=instance, schema=schema)
    instance["transaction_time"].pop("recorded_until")
    try:
        validate(instance=instance, schema=schema)
        raise AssertionError("should have failed")
    except ValidationError:
        pass
