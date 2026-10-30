import tempfile
from pathlib import Path

from storygram import validate


def test_validate_empty_archive():
    d = Path(tempfile.mkdtemp())
    # create structure
    for sub in ["data/episodes", "data/assertions"]:
        (d / sub).mkdir(parents=True, exist_ok=True)
    res = validate.validate_archive(d)
    assert res["ok"]
