"""SQLite/FTS5 index for search."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any


def build_index(root: Path) -> Path:
    db_path = root / "generated" / "index.db"
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    cur = conn.cursor()
    cur.execute("CREATE TABLE IF NOT EXISTS records(id TEXT PRIMARY KEY, type TEXT, data TEXT)")
    cur.execute("CREATE VIRTUAL TABLE IF NOT EXISTS records_fts USING fts5(id, type, content)")
    # index all json files in data/
    for p in (root / "data").rglob("*.json"):
        try:
            data = json.loads(p.read_text())
            if isinstance(data, dict) and "id" in data:
                rid = data["id"]
                rtype = data.get("type", "")
                cur.execute(
                    "REPLACE INTO records(id,type,data) VALUES(?,?,?)",
                    (rid, rtype, json.dumps(data)),
                )
                # content
                content = json.dumps(data)
                cur.execute(
                    "REPLACE INTO records_fts(id,type,content) VALUES(?,?,?)", (rid, rtype, content)
                )
        except Exception:
            continue
    conn.commit()
    conn.close()
    return db_path


def search(root: Path, query: str) -> list[dict[str, Any]]:
    db_path = root / "generated" / "index.db"
    if not db_path.exists():
        build_index(root)
    conn = sqlite3.connect(str(db_path))
    cur = conn.cursor()
    try:
        cur.execute("SELECT id,type FROM records_fts WHERE records_fts MATCH ? LIMIT 100", (query,))
        rows = cur.fetchall()
    except Exception:
        cur.execute(
            "SELECT id,type FROM records WHERE id LIKE ? OR type LIKE ? LIMIT 100",
            (f"%{query}%", f"%{query}%"),
        )
        rows = cur.fetchall()
    conn.close()
    return [{"id": r[0], "type": r[1]} for r in rows]
