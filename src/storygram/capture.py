"""Inbox-only capture ingestion with checksummed capture metadata."""

from __future__ import annotations

import hashlib
import json
import mimetypes
import os
import shutil
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

CAPTURE_FORMAT = "storygram.capture/1"
CAPTURE_METADATA_DIRNAME = ".storygram"
_CHUNK_SIZE = 1024 * 1024


class CaptureError(Exception):
    """Raised when a capture cannot be copied or recorded safely."""


def metadata_path(root: Path, filename: str) -> Path:
    """Return the sidecar metadata path for a capture filename."""
    return Path(root) / "inbox" / CAPTURE_METADATA_DIRNAME / f"{filename}.json"


def _copy_and_hash(source: Path, destination: Path) -> tuple[int, str]:
    digest = hashlib.sha256()
    size = 0
    with source.open("rb") as src, destination.open("wb") as dst:
        while chunk := src.read(_CHUNK_SIZE):
            dst.write(chunk)
            digest.update(chunk)
            size += len(chunk)
    return size, digest.hexdigest()


def ingest_capture(
    root: Path,
    source: Path,
    *,
    overwrite: bool = False,
    now: str | None = None,
) -> dict[str, Any]:
    """Copy a capture into ``inbox/`` and write its metadata sidecar.

    The capture itself stays unchanged and canonical ``data/`` is never touched.
    """
    root = Path(root)
    source = Path(source)
    if not source.is_file():
        raise CaptureError(f"Capture source is not a file: {source}")

    inbox = root / "inbox"
    target = inbox / source.name
    existed = target.exists()
    if existed and not overwrite:
        raise CaptureError(f"Capture already exists: {target}; use --overwrite to replace it")

    inbox.mkdir(parents=True, exist_ok=True)
    metadata_directory = inbox / CAPTURE_METADATA_DIRNAME
    metadata_directory.mkdir(parents=True, exist_ok=True)
    sidecar = metadata_path(root, source.name)

    temporary_target = target.with_name(f".{target.name}.tmp-{os.getpid()}")
    temporary_metadata = sidecar.with_name(f".{sidecar.name}.tmp-{os.getpid()}")
    capture_replaced = False
    try:
        size, checksum = _copy_and_hash(source, temporary_target)
        shutil.copystat(source, temporary_target)
        metadata = {
            "format": CAPTURE_FORMAT,
            "filename": target.name,
            "size": size,
            "mime_type": mimetypes.guess_type(target.name)[0],
            "checksum": {"algorithm": "sha256", "value": checksum},
            "ingested_at": now or datetime.now(UTC).isoformat(),
            "overwritten": existed,
        }
        temporary_metadata.write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
        os.replace(temporary_target, target)
        capture_replaced = True
        os.replace(temporary_metadata, sidecar)
    except Exception as exc:
        temporary_target.unlink(missing_ok=True)
        temporary_metadata.unlink(missing_ok=True)
        if capture_replaced:
            sidecar.unlink(missing_ok=True)
        raise CaptureError(f"Cannot ingest {source}: {exc}") from exc

    return {**metadata, "path": str(target), "metadata_path": str(sidecar)}
