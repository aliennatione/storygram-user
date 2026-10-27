"""Export functionality."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def export_json(root: Path, visibility_filter: set[str] | None = None) -> list[dict[str, Any]]:
    results = []
    for sub in ["episodes", "people", "organizations", "places", "periods", "events",
                "relationships", "sources", "media-assets", "assertions", "annotations",
                "narratives", "conflicts", "collections"]:
        for p in (root / "data" / sub).rglob("*.json"):
            try:
                data = json.loads(p.read_text())
            except Exception:
                continue
            if visibility_filter and isinstance(data, dict):
                vis = data.get("visibility")
                if vis and vis not in visibility_filter:
                    continue
            results.append(data)
    return results


def export_jsonld(root: Path, visibility_filter: set[str] | None = None) -> dict[str, Any]:
    items = export_json(root, visibility_filter)
    return {"@context": "https://storygram.local/context", "@graph": items}
