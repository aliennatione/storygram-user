"""Bitemporal helpers."""

from __future__ import annotations

from typing import Any


def is_current_transaction(assertion: dict[str, Any]) -> bool:
    tt = assertion.get("transaction_time") or {}
    return tt.get("recorded_until") is None


def supersedes_chain(assertions: list[dict[str, Any]]) -> dict[str, list[str]]:
    children: dict[str, list[str]] = {}
    for a in assertions:
        child_id = a.get("id")
        if not isinstance(child_id, str):
            continue
        for s in a.get("supersedes") or []:
            children.setdefault(s, []).append(child_id)
    return children
