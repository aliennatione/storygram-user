"""Conflict listing."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def list_conflicts(root: Path, status: str | None = None) -> list[dict[str, Any]]:
    results = []
    for p in (root / "data" / "conflicts").rglob("*.json"):
        try:
            data = json.loads(p.read_text())
        except Exception:
            continue
        if status and data.get("status") != status:
            continue
        results.append(data)
    # also find from assertions contradicts
    if not results:
        for p in (root / "data" / "assertions").rglob("*.json"):
            try:
                data = json.loads(p.read_text())
                if data.get("contradicts"):
                    results.append(
                        {
                            "id": f"from:{data['id']}",
                            "assertions": [data["id"]] + data.get("contradicts", []),
                            "status": "open",
                        }
                    )
            except Exception:
                continue
    return results
