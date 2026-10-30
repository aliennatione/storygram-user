import json
import tempfile
from pathlib import Path

from storygram import export


def test_export_json_filters_visibility():
    d = Path(tempfile.mkdtemp())
    for sub in ["data/assertions", "data/people"]:
        (d / sub).mkdir(parents=True, exist_ok=True)
    (d / "data" / "assertions" / "a1.json").write_text(
        json.dumps(
            {
                "id": "assertion:01",
                "type": "Assertion",
                "subject": "person:01",
                "predicate": "relation:lived_in",
                "status": "reported",
                "transaction_time": {
                    "recorded_at": "2026-01-01T00:00:00+00:00",
                    "recorded_until": None,
                },
                "created_at": "2026-01-01T00:00:00+00:00",
                "updated_at": "2026-01-01T00:00:00+00:00",
                "visibility": "private",
            }
        )
    )
    res = export.export_json(d, visibility_filter={"family", "public"})
    assert len(res) == 0
    res = export.export_json(d, visibility_filter={"private"})
    assert len(res) == 1
