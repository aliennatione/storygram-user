"""SQLite/FTS5 index for deterministic local search."""

from __future__ import annotations

import hashlib
import json
import sqlite3
from pathlib import Path
from typing import Any

from .registry import RECORD_TYPES


def _indexed_paths(root: Path) -> list[Path]:
    paths = []
    for record_type in RECORD_TYPES:
        if record_type.name == "Proposal":
            continue
        paths.extend(sorted((root / "data" / record_type.directory).rglob("*.json")))
    return sorted(paths)


def _signature(root: Path) -> str:
    digest = hashlib.sha256()
    for path in _indexed_paths(root):
        try:
            stat = path.stat()
        except OSError:
            continue
        digest.update(str(path.relative_to(root)).encode())
        digest.update(str(stat.st_mtime_ns).encode())
        digest.update(str(stat.st_size).encode())
    return digest.hexdigest()


def _connect(db_path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    return conn


def build_index(root: Path, errors: list[str] | None = None) -> Path:
    db_path = root / "generated" / "index.db"
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = _connect(db_path)
    try:
        cur = conn.cursor()
        cur.execute("DROP TABLE IF EXISTS records")
        cur.execute("DROP TABLE IF EXISTS records_fts")
        cur.execute("DROP TABLE IF EXISTS records_meta")
        cur.execute("CREATE TABLE records(id TEXT PRIMARY KEY, type TEXT, data TEXT)")
        cur.execute("CREATE VIRTUAL TABLE records_fts USING fts5(id, type, content)")
        cur.execute("CREATE TABLE records_meta(key TEXT PRIMARY KEY, value TEXT)")
        for path in _indexed_paths(root):
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as exc:
                if errors is not None:
                    errors.append(f"{path}: {exc}")
                continue
            if not isinstance(data, dict) or not isinstance(data.get("id"), str):
                if errors is not None:
                    errors.append(f"{path}: expected a JSON object with an id")
                continue
            record_id = data["id"]
            record_type = str(data.get("type", ""))
            content = json.dumps(data, sort_keys=True)
            cur.execute(
                "INSERT OR REPLACE INTO records(id,type,data) VALUES(?,?,?)",
                (record_id, record_type, content),
            )
            cur.execute(
                "INSERT INTO records_fts(id,type,content) VALUES(?,?,?)",
                (record_id, record_type, content),
            )
        cur.execute(
            "INSERT INTO records_meta(key,value) VALUES('signature',?)",
            (_signature(root),),
        )
        conn.commit()
    finally:
        conn.close()
    return db_path


def _is_current(root: Path, db_path: Path) -> bool:
    try:
        conn = _connect(db_path)
        try:
            row = conn.execute("SELECT value FROM records_meta WHERE key='signature'").fetchone()
        finally:
            conn.close()
    except sqlite3.Error:
        return False
    return row is not None and row["value"] == _signature(root)


def _fts_query(query: str) -> str:
    return '"' + query.replace('"', '""') + '"'


def search(root: Path, query: str, rebuild: bool = False) -> list[dict[str, Any]]:
    db_path = root / "generated" / "index.db"
    if rebuild or not db_path.exists() or not _is_current(root, db_path):
        build_index(root)
    conn = _connect(db_path)
    try:
        rows = conn.execute(
            "SELECT id,type FROM records WHERE id = ? ORDER BY id LIMIT 100",
            (query,),
        ).fetchall()
        if not rows:
            rows = conn.execute(
                "SELECT id,type FROM records WHERE type = ? COLLATE NOCASE ORDER BY id LIMIT 100",
                (query,),
            ).fetchall()
        if not rows:
            try:
                rows = conn.execute(
                    "SELECT id,type FROM records_fts "
                    "WHERE records_fts MATCH ? ORDER BY id LIMIT 100",
                    (_fts_query(query),),
                ).fetchall()
            except sqlite3.Error:
                rows = []
        if not rows:
            rows = conn.execute(
                "SELECT id,type FROM records WHERE id LIKE ? OR type LIKE ? OR data LIKE ? "
                "ORDER BY id LIMIT 100",
                (f"%{query}%", f"%{query}%", f"%{query}%"),
            ).fetchall()
    finally:
        conn.close()
    return [{"id": row["id"], "type": row["type"]} for row in rows]
