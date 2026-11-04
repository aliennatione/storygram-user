"""Checksummed manifest for media files stored outside Git."""

from __future__ import annotations

import hashlib
import json
import mimetypes
import os
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

MANIFEST_FORMAT = "storygram.media-manifest/1"
VISIBILITIES = ("private", "restricted", "family", "public")


class MediaError(Exception):
    """Raised when a media manifest entry cannot be written."""


def manifest_dir(root: Path) -> Path:
    return Path(root) / "media-manifest"


def _slug(value: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9._~-]+", "-", value).strip("-.").lower()
    return slug or "media"


def _checksum(path: Path) -> tuple[str, int]:
    digest = hashlib.sha256()
    size = 0
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
            size += len(chunk)
    return digest.hexdigest(), size


def add_media(
    root: Path,
    file_path: Path | str,
    *,
    uri: str | None = None,
    visibility: str | None = None,
    acquired_at: str | None = None,
    notes: str | None = None,
    name: str | None = None,
    overwrite: bool = False,
    now: str | None = None,
) -> dict[str, Any]:
    """Register an external media file in the local manifest.

    The media file itself is never copied or committed; only checksummed
    metadata is written under ``media-manifest/``.
    """
    source = Path(file_path)
    if not source.exists() or not source.is_file():
        raise MediaError(f"media file not found: {source}")
    if visibility is not None and visibility not in VISIBILITIES:
        raise MediaError(f"unsupported visibility: {visibility}")

    checksum, size = _checksum(source)
    label = name or source.name
    target = manifest_dir(Path(root)) / f"{_slug(Path(label).stem)}-{checksum[:8]}.json"
    if target.exists() and not overwrite:
        raise MediaError(
            f"manifest entry already exists: {target.name} (use --overwrite to refresh)"
        )

    mime_type, _ = mimetypes.guess_type(source.name)
    entry: dict[str, Any] = {
        "format": MANIFEST_FORMAT,
        "id": f"media-manifest/{target.stem}",
        "filename": source.name,
        "uri": uri if uri is not None else str(source),
        "checksum": {"algorithm": "sha256", "value": checksum},
        "mime_type": mime_type,
        "size": size,
        "registered_at": now or datetime.now(UTC).isoformat(),
    }
    if visibility:
        entry["visibility"] = visibility
    if acquired_at:
        entry["acquired_at"] = acquired_at
    if notes:
        entry["notes"] = notes

    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_name(f".{target.name}.tmp-{os.getpid()}")
    temporary.write_text(json.dumps(entry, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    os.replace(temporary, target)
    return entry


def list_media(root: Path) -> list[dict[str, Any]]:
    """Return every manifest entry sorted by ID."""
    directory = manifest_dir(Path(root))
    if not directory.exists():
        return []
    entries: list[dict[str, Any]] = []
    for path in sorted(directory.glob("*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if isinstance(data, dict):
            entries.append(data)
    return sorted(entries, key=lambda item: str(item.get("id", "")))
