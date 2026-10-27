import json
from pathlib import Path

from jsonschema import validate


def test_ingest_episode_does_not_confirm():
    ep_schema = json.loads(Path("schema/episode.schema.json").read_text())
    ep = json.loads(Path("tests/fixtures/episode_interview.json").read_text())
    validate(instance=ep, schema=ep_schema)
    # Episode status is reported/not confirmed; ingestion should not create confirmed facts
    assert ep["status"] != "confirmed"
