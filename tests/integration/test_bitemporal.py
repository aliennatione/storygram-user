import json
from pathlib import Path

from jsonschema import validate


def test_bitemporal_supersession_example():
    ep_schema = json.loads(Path("schema/episode.schema.json").read_text())
    as_schema = json.loads(Path("schema/assertion.schema.json").read_text())

    ep = json.loads(Path("tests/fixtures/episode_interview.json").read_text())
    validate(instance=ep, schema=ep_schema)

    a1 = json.loads(Path("tests/fixtures/assertion_lived_in.json").read_text())
    validate(instance=a1, schema=as_schema)
    assert a1["transaction_time"]["recorded_until"] is None

    a2 = json.loads(Path("tests/fixtures/assertion_lived_in_superseding.json").read_text())
    validate(instance=a2, schema=as_schema)
    assert "assertion:01" in a2["supersedes"]
