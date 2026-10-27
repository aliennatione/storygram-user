import json
from pathlib import Path
import tempfile

from storygram import validate


def test_inbox_not_canonical():
    d = Path(tempfile.mkdtemp())
    for sub in ["data/episodes", "data/assertions", "inbox", "proposals"]:
        (d / sub).mkdir(parents=True, exist_ok=True)
    (d / "inbox" / "ep.json").write_text(json.dumps({
        "id": "episode:x1", "type": "Episode", "episode_type": "memory",
        "status": "reported", "created_at": "2026-01-01T00:00:00+00:00",
        "updated_at": "2026-01-01T00:00:00+00:00"
    }))
    res = validate.validate_archive(d)
    assert res["ok"]  # validation focuses on data/, not inbox by default
