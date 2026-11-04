"""Git integration checks."""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any

from . import validate


def get_changed_files(root: Path, base: str | None = None) -> list[Path]:
    try:
        if base:
            result = subprocess.run(
                ["git", "-C", str(root), "diff", "--name-only", f"{base}...HEAD"],
                capture_output=True,
                text=True,
                check=False,
            )
        else:
            result = subprocess.run(
                ["git", "-C", str(root), "diff", "--name-only", "HEAD"],
                capture_output=True,
                text=True,
                check=False,
            )
        files = []
        for line in result.stdout.splitlines():
            line = line.strip()
            if not line:
                continue
            p = root / line
            if p.exists() and p.is_file():
                files.append(p)
        return files
    except Exception:
        return []


def git_check(root: Path, base: str | None = None) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []
    changed = get_changed_files(root, base)
    # also validate whole archive
    res = validate.validate_archive(root)
    if not res["ok"]:
        errors.extend(res["errors"])
    warnings.extend(res.get("warnings", []))
    return {
        "ok": len(errors) == 0,
        "errors": errors,
        "warnings": warnings,
        "changed_files": [str(c) for c in changed],
    }
