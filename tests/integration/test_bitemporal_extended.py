import json
from pathlib import Path

from jsonschema import validate


def test_transaction_time_queryable_separately():
    as_schema = json.loads(Path("schema/assertion.schema.json").read_text())
    a1 = json.loads(Path("tests/fixtures/assertion_lived_in.json").read_text())
    a2 = json.loads(Path("tests/fixtures/assertion_lived_in_superseding.json").read_text())
    validate(instance=a1, schema=as_schema)
    validate(instance=a2, schema=as_schema)
    assert a1["transaction_time"]["recorded_until"] is None
    assert a2["transaction_time"]["recorded_until"] is None
    assert a1["valid_time"]["end"] == "1995"
    assert a2["valid_time"]["end"] == "1994"
