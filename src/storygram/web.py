"""Minimal local web UI for proposal review."""

from __future__ import annotations

import html
import json
from collections.abc import Callable
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, cast
from urllib.parse import parse_qs, quote, unquote, urlparse

from . import proposals as proposals_mod
from . import validate as validate_mod
from .genogram import build_genogram
from .llm import (
    LLMAdapter,
    LLMAdapterError,
    Provider,
    ProviderConfig,
    provider_config,
    provider_from_config,
    save_pending,
)
from .registry import RECORD_TYPES, iter_reference_strings
from .timeline import build_timeline

MAX_BODY = 4 * 1024 * 1024


class APIRequestError(Exception):
    def __init__(self, status: int, message: str):
        self.status = status
        self.message = message
        super().__init__(message)


def _esc(value: Any) -> str:
    return html.escape(str(value), quote=True)


def _layout(title: str, body: str) -> str:
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{_esc(title)} - Storygram</title>
<style>
:root {{ color-scheme: light dark; --line:#d0d7de; --muted:#57606a; --accent:#0969da; }}
* {{ box-sizing: border-box; }}
body {{ margin:0; font-family: system-ui, sans-serif; line-height:1.45; }}
header {{
  border-bottom:1px solid var(--line); padding:12px 24px;
  display:flex; gap:20px; align-items:center;
}}
header strong {{ font-size:1.1rem; }}
nav a {{ margin-right:14px; color:var(--accent); text-decoration:none; }}
main {{ max-width:1100px; margin:0 auto; padding:24px; }}
table {{ width:100%; border-collapse:collapse; margin:12px 0; }}
th, td {{ text-align:left; border-bottom:1px solid var(--line); padding:8px; vertical-align:top; }}
pre {{ background:#8881; padding:12px; overflow:auto; border-radius:6px; }}
textarea {{
  width:100%; min-height:420px; font-family:ui-monospace, monospace;
  font-size:13px; padding:12px;
}}
button, .button {{
  display:inline-block; padding:7px 12px; border:1px solid var(--line);
  border-radius:6px; background:#8881; color:inherit; cursor:pointer;
  text-decoration:none;
}}
button.primary {{ background:var(--accent); color:white; border-color:var(--accent); }}
.error {{ border-left:4px solid #cf222e; padding:8px 12px; background:#cf222e20; margin:12px 0; }}
.ok {{ border-left:4px solid #1a7f37; padding:8px 12px; background:#1a7f3720; margin:12px 0; }}
.muted {{ color:var(--muted); }}
.badge {{ border:1px solid var(--line); border-radius:999px; padding:2px 8px; font-size:.85rem; }}
.filters {{ display:flex; flex-wrap:wrap; gap:12px; align-items:end; margin:16px 0; }}
.filters label {{ display:flex; flex-direction:column; gap:4px; font-size:.9rem; }}
.filters input, .filters select {{
  padding:7px 9px; border:1px solid var(--line); border-radius:6px;
  background:Canvas; color:CanvasText;
}}
.warning {{ border-left:4px solid #9a6700; padding:8px 12px; background:#9a670020; margin:12px 0; }}
.intervals {{ margin:4px 0 0; padding-left:18px; font-size:.9rem; }}
</style>
</head>
<body>
<header>
  <strong>Storygram</strong>
  <nav>
    <a href="/">Home</a><a href="/records">Records</a><a href="/timeline">Timeline</a>
    <a href="/genogram">Genogram</a><a href="/proposals">Proposals</a>
    <a href="/proposals/new">New proposal</a>
    <a href="/proposals/generate">Generate</a>
  </nav>
</header>
<main>{body}</main>
</body>
</html>"""


def _errors_block(errors: list[str]) -> str:
    if not errors:
        return ""
    items = "".join(f"<li>{_esc(error)}</li>" for error in errors)
    return f'<div class="error"><strong>Could not continue</strong><ul>{items}</ul></div>'


def _status_badge(status: Any) -> str:
    return f'<span class="badge">{_esc(status or "unknown")}</span>'


def _query_value(query: str, key: str) -> str:
    values = parse_qs(query, keep_blank_values=True).get(key)
    return values[0].strip() if values else ""


def _relative_label(root: Path, path: Path) -> str:
    try:
        return str(path.relative_to(root))
    except ValueError:
        return str(path)


def _record_href(record_id: str) -> str:
    return f"/records/{quote(record_id, safe='')}"


def _record_name(data: dict[str, Any]) -> str:
    for key in ("title", "name", "summary"):
        value = data.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


def _record_search_text(data: dict[str, Any]) -> str:
    parts = [data.get(key) for key in ("id", "type", "status", "title", "name", "summary", "notes")]
    tags = data.get("tags")
    if isinstance(tags, list):
        parts.extend(tags)
    return "\n".join(str(part) for part in parts if part is not None)


def _notice_block(title: str, items: list[str]) -> str:
    if not items:
        return ""
    rendered = "".join(f"<li>{_esc(item)}</li>" for item in items)
    return f'<div class="warning"><strong>{_esc(title)}</strong><ul>{rendered}</ul></div>'


def _warning_block(items: list[str]) -> str:
    return _notice_block("Some records could not be loaded", items)


def _record_links(ids: list[str], known_ids: set[str]) -> str:
    if not ids:
        return '<p class="muted">None.</p>'
    items = []
    for record_id in ids:
        if record_id in known_ids:
            href = _record_href(record_id)
            items.append(f'<li><a href="{_esc(href)}">{_esc(record_id)}</a></li>')
        else:
            items.append(f'<li><span class="muted">{_esc(record_id)} (missing)</span></li>')
    return f"<ul>{''.join(items)}</ul>"


def _known_ids(records: list[tuple[Path, dict[str, Any]]]) -> set[str]:
    return {str(data["id"]) for _, data in records if isinstance(data.get("id"), str)}


def _record_link(record_id: Any, known_ids: set[str]) -> str:
    if not isinstance(record_id, str) or not record_id:
        return '<span class="muted">—</span>'
    if record_id in known_ids:
        href = _record_href(record_id)
        return f'<a href="{_esc(href)}">{_esc(record_id)}</a>'
    return f'<span class="muted">{_esc(record_id)} (missing)</span>'


def _interval_label(value: Any) -> str:
    if not isinstance(value, dict):
        return "—"
    start = value.get("start")
    if start is None:
        start = value.get("recorded_at")
    end = value.get("end")
    if end is None:
        end = value.get("recorded_until")
    precision = value.get("precision")
    parts = []
    if start is not None:
        parts.append(str(start))
    if end is not None:
        parts.append(f"→ {end}")
    if precision is not None:
        parts.append(f"({precision})")
    return " ".join(parts) if parts else "—"


def _interval_cell(representative: Any, aggregated: list[Any]) -> str:
    primary = _esc(_interval_label(representative))
    if not aggregated:
        return primary
    items = "".join(f"<li>{_esc(_interval_label(value))}</li>" for value in aggregated)
    return f'{primary}<ul class="intervals">{items}</ul>'


def _proposal_rows(root: Path) -> str:
    entries = proposals_mod.list_proposals(root, include_applied=True)
    if not entries:
        return '<p class="muted">No proposals yet.</p>'
    rows = []
    for path, data in entries:
        proposal_id = str(data.get("id", ""))
        href = f"/proposals/{quote(proposal_id, safe='')}"
        rows.append(
            "<tr>"
            f'<td><a href="{_esc(href)}">{_esc(proposal_id)}</a></td>'
            f"<td>{_status_badge(data.get('status'))}</td>"
            f"<td>{_esc(data.get('title') or '')}</td>"
            f"<td>{len(data.get('operations') or [])}</td>"
            f'<td class="muted">{_esc(path.parent.name)}</td>'
            "</tr>"
        )
    return (
        "<table><thead><tr><th>ID</th><th>Status</th><th>Title</th>"
        "<th>Operations</th><th>Location</th></tr></thead><tbody>"
        + "".join(rows)
        + "</tbody></table>"
    )


def render_home(root: Path) -> str:
    result = validate_mod.validate_archive(root)
    records, load_errors = validate_mod.load_records(root)
    pending = proposals_mod.list_proposals(root, include_applied=False)
    applied = proposals_mod.list_proposals(root, include_applied=True)
    applied = [(path, data) for path, data in applied if data.get("status") == "merged"]
    status = '<div class="ok">Archive validates.</div>'
    if not result["ok"]:
        status = _errors_block(load_errors + result["errors"])
    counts = []
    for record_type in RECORD_TYPES:
        count = sum(1 for _, data in records if data.get("type") == record_type.name)
        counts.append(f"<li>{_esc(record_type.name)}: {count}</li>")
    body = f"""
<h1>Storygram</h1>
<p class="muted">Local-first review surface. Canonical changes require approval.</p>
{status}
<h2>Review queue</h2>
<table><thead><tr><th>Pending</th><th>Merged</th><th>Records</th></tr></thead>
<tbody><tr><td>{len(pending)}</td><td>{len(applied)}</td><td>{len(records)}</td></tr></tbody></table>
<p>
  <a class="button" href="/records">Browse records</a>
  <a class="button" href="/timeline">Timeline</a>
  <a class="button" href="/genogram">Genogram</a>
  <a class="button primary" href="/proposals/new">Create proposal</a>
  <a class="button" href="/proposals/generate">Generate with Ollama</a>
  <a class="button" href="/proposals">View proposals</a>
</p>
<h2>Record counts</h2><ul>{"".join(counts)}</ul>
"""
    return _layout("Home", body)


def render_records(root: Path, query: str = "") -> str:
    record_type = _query_value(query, "type")
    status = _query_value(query, "status")
    needle = _query_value(query, "q")
    records, load_errors = validate_mod.load_records(root)

    filtered = []
    for path, data in records:
        if record_type and data.get("type") != record_type:
            continue
        if status and data.get("status") != status:
            continue
        if needle and needle.casefold() not in _record_search_text(data).casefold():
            continue
        filtered.append((path, data))
    filtered.sort(key=lambda item: (str(item[1].get("id") or ""), _relative_label(root, item[0])))

    rows = []
    for path, data in filtered:
        record_id = data.get("id")
        if isinstance(record_id, str) and record_id:
            href = _record_href(record_id)
            id_cell = f'<a href="{_esc(href)}">{_esc(record_id)}</a>'
        else:
            id_cell = '<span class="muted">(missing id)</span>'
        name = _record_name(data)
        rows.append(
            "<tr>"
            f"<td>{id_cell}</td>"
            f"<td>{_esc(data.get('type') or '')}</td>"
            f"<td>{_status_badge(data.get('status'))}</td>"
            f"<td>{_esc(name)}</td>"
            f"<td>{_esc(data.get('updated_at') or '')}</td>"
            f'<td class="muted">{_esc(_relative_label(root, path))}</td>'
            "</tr>"
        )

    table = '<p class="muted">No records match these filters.</p>'
    if rows:
        table = (
            "<table><thead><tr><th>ID</th><th>Type</th><th>Status</th>"
            "<th>Name / title</th><th>Updated</th><th>File</th></tr></thead><tbody>"
            + "".join(rows)
            + "</tbody></table>"
        )

    type_options = "".join(
        f'<option value="{_esc(item.name)}"'
        f"{' selected' if item.name == record_type else ''}>{_esc(item.name)}</option>"
        for item in RECORD_TYPES
    )
    body = f"""
<h1>Records</h1>
<p class="muted">
Read-only canonical record browser. Showing {len(filtered)} of {len(records)} records.
</p>
{_warning_block(load_errors)}
<form class="filters" method="get" action="/records">
  <label>Type <select name="type"><option value="">All types</option>{type_options}</select></label>
  <label>Status <input name="status" value="{_esc(status)}" placeholder="confirmed"></label>
  <label>Search <input name="q" value="{_esc(needle)}" placeholder="id, name, notes"></label>
  <button type="submit">Filter</button>
  <a class="button" href="/records">Reset</a>
</form>
{table}
"""
    return _layout("Records", body)


def render_record_detail(root: Path, record_id: str) -> tuple[int, str]:
    records, load_errors = validate_mod.load_records(root)
    match = next(
        ((path, data) for path, data in records if data.get("id") == record_id),
        None,
    )
    if match is None:
        return 404, _layout(
            "Not found",
            f"<h1>Record not found</h1><p>{_esc(record_id or '(empty id)')}</p>"
            '<p><a class="button" href="/records">Back to records</a></p>',
        )

    path, data = match
    known_ids = {str(item.get("id")) for _, item in records if isinstance(item.get("id"), str)}
    references = sorted(set(iter_reference_strings(data)))
    backlinks = sorted(
        {
            str(item.get("id"))
            for _, item in records
            if isinstance(item.get("id"), str)
            and item.get("id") != record_id
            and record_id in set(iter_reference_strings(item))
        }
    )
    name = _record_name(data) or record_id
    visibility = data.get("visibility")
    visibility_badge = f'<span class="badge">{_esc(visibility)}</span>' if visibility else ""
    body = f"""
<p><a class="button" href="/records">Back to records</a></p>
<h1>{_esc(name)}</h1>
<p><span class="badge">{_esc(data.get("type") or "unknown")}</span>
{_status_badge(data.get("status"))} {visibility_badge}</p>
<p class="muted">{_esc(record_id)} · {_esc(_relative_label(root, path))}</p>
{_warning_block(load_errors)}
<h2>References</h2>
{_record_links(references, known_ids)}
<h2>Referenced by</h2>
{_record_links(backlinks, known_ids)}
<h2>Record JSON</h2>
<pre>{_esc(json.dumps(data, indent=2, ensure_ascii=False))}</pre>
"""
    return 200, _layout(record_id, body)


def render_timeline(root: Path, query: str = "") -> tuple[int, str]:
    record_id = _query_value(query, "id")
    records, load_errors = validate_mod.load_records(root)
    known_ids = _known_ids(records)
    if record_id and record_id not in known_ids:
        return 404, _layout(
            "Timeline not found",
            f"<h1>Unknown record</h1><p>{_esc(record_id)}</p>"
            '<p><a class="button" href="/timeline">Back to archive timeline</a></p>',
        )

    entries = build_timeline(root, record_id or None)
    rows = []
    for entry in entries:
        evidence = sorted(
            set(entry.get("produced_by") or []) | set(entry.get("supported_by") or [])
        )
        rows.append(
            "<tr>"
            f"<td>{_esc(_interval_label(entry.get('valid_time')))}</td>"
            f"<td>{_record_link(entry.get('assertion_id'), known_ids)}</td>"
            f"<td>{_record_link(entry.get('subject'), known_ids)}</td>"
            f"<td>{_esc(entry.get('predicate') or '')}</td>"
            f"<td>{_record_link(entry.get('object'), known_ids)}</td>"
            f"<td>{_status_badge(entry.get('status'))}</td>"
            f"<td>{_esc(_interval_label(entry.get('transaction_time')))}</td>"
            f"<td>{_record_links(evidence, known_ids)}</td>"
            "</tr>"
        )

    scope = record_id or "archive"
    table = f'<p class="muted">No timeline entries for {_esc(scope)}.</p>'
    if rows:
        table = (
            "<table><thead><tr><th>Valid time</th><th>Assertion</th><th>Subject</th>"
            "<th>Predicate</th><th>Object</th><th>Status</th>"
            "<th>Transaction time</th><th>Evidence</th></tr></thead><tbody>"
            + "".join(rows)
            + "</tbody></table>"
        )

    body = f"""
<h1>Timeline</h1>
<p class="muted">
Read-only timeline derived from open assertions. Scope: {_esc(scope)}.
</p>
{_warning_block(load_errors)}
<form class="filters" method="get" action="/timeline">
  <label>Record ID
    <input name="id" value="{_esc(record_id)}"
           placeholder="person:... / place:... / collection:..."></label>
  <button type="submit">Show timeline</button>
  <a class="button" href="/timeline">Archive timeline</a>
</form>
{table}
"""
    return 200, _layout("Timeline", body)


def render_genogram(root: Path, query: str = "") -> tuple[int, str]:
    person_id = _query_value(query, "id")
    records, load_errors = validate_mod.load_records(root)
    known_ids = _known_ids(records)
    form = f"""
<form class="filters" method="get" action="/genogram">
  <label>Person ID
    <input name="id" value="{_esc(person_id)}" placeholder="person:..."></label>
  <button type="submit">Show genogram</button>
</form>
"""
    if not person_id:
        return 400, _layout(
            "Genogram",
            "<h1>Genogram</h1>"
            '<p class="muted">Experimental relationship view. Provide a person ID.</p>'
            f"{_errors_block(['Provide a person ID'])}{form}",
        )
    if person_id not in known_ids:
        return 404, _layout(
            "Genogram not found",
            f"<h1>Unknown record</h1><p>{_esc(person_id)}</p>"
            '<p><a class="button" href="/genogram">Back to genogram</a></p>',
        )

    result = build_genogram(root, person_id)
    rows = []
    for relation in result["relations"]:
        supported = relation.get("supported")
        supported_badge = (
            '<span class="badge">supported</span>'
            if supported
            else '<span class="badge">unsupported</span>'
        )
        related = relation.get("related_ids") or []
        valid_cell = _interval_cell(relation.get("valid_time"), relation.get("valid_times") or [])
        transaction_cell = _interval_cell(
            relation.get("transaction_time"), relation.get("transaction_times") or []
        )
        rows.append(
            "<tr>"
            f"<td>{_esc(relation.get('predicate') or '')}</td>"
            f"<td>{_esc(relation.get('direction') or '')}</td>"
            f"<td>{_record_link(relation.get('subject'), known_ids)}</td>"
            f"<td>{_record_link(relation.get('object'), known_ids)}</td>"
            f"<td>{supported_badge}</td>"
            f"<td>{_record_link(relation.get('record_id'), known_ids)}</td>"
            f"<td>{valid_cell}</td>"
            f"<td>{transaction_cell}</td>"
            f"<td>{_record_links(related, known_ids)}</td>"
            "</tr>"
        )

    table = f'<p class="muted">No relations for {_esc(person_id)}.</p>'
    if rows:
        table = (
            "<table><thead><tr><th>Predicate</th><th>Direction</th><th>Subject</th>"
            "<th>Object</th><th>Supported</th><th>Source record</th>"
            "<th>Valid time / valid_times</th>"
            "<th>Transaction time / transaction_times</th><th>Related records</th>"
            "</tr></thead><tbody>" + "".join(rows) + "</tbody></table>"
        )

    body = f"""
<h1>Genogram: {_esc(person_id)}</h1>
<div class="warning">
<strong>Experimental</strong>
<p>This relationship view is experimental and has no temporal filter yet.
It derives only from canonical records and never writes data.</p>
</div>
<p class="muted">
Read-only, derived from <code>relation:*</code> assertions and endpoint-aware
Relationship records.
</p>
{_warning_block(load_errors)}
{_notice_block("Genogram warnings", result["warnings"])}
{form}
{table}
"""
    return 200, _layout(f"Genogram {person_id}", body)


def render_list(root: Path) -> str:
    body = (
        "<h1>Proposals</h1>"
        '<p><a class="button primary" href="/proposals/new">New proposal</a> '
        '<a class="button" href="/proposals/generate">Generate with Ollama</a></p>'
        f"{_proposal_rows(root)}"
    )
    return _layout("Proposals", body)


def _new_form(value: str = "", errors: list[str] | None = None) -> str:
    body = f"""
<h1>New proposal</h1>
<p class="muted">
Paste a proposal JSON object. It is saved as pending only; approval is a separate action.
</p>
{_errors_block(errors or [])}
<form method="post" action="/proposals/new">
<textarea name="json" spellcheck="false">{_esc(value)}</textarea>
<p>
  <button class="primary" type="submit">Save pending proposal</button>
  <a class="button" href="/proposals">Cancel</a>
</p>
</form>
"""
    return _layout("New proposal", body)


def _edit_form(proposal_id: str, value: str = "", errors: list[str] | None = None) -> str:
    body = f"""
<h1>Edit proposal</h1>
<p class="muted">
Editing {_esc(proposal_id)}. The proposal ID cannot change; saving replaces the pending JSON.
</p>
{_errors_block(errors or [])}
<form method="post" action="/proposals/{quote(proposal_id, safe="")}/edit">
<textarea name="json" spellcheck="false">{_esc(value)}</textarea>
<p>
  <button class="primary" type="submit">Save pending proposal</button>
  <a class="button" href="/proposals/{quote(proposal_id, safe="")}">Cancel</a>
</p>
</form>
"""
    return _layout(f"Edit {proposal_id}", body)


def render_generate_form(
    source: str = "",
    errors: list[str] | None = None,
    model: str | None = None,
    base_url: str | None = None,
    provider: str | None = None,
) -> str:
    try:
        config = provider_config(provider, model, base_url)
    except LLMAdapterError:
        config = ProviderConfig(provider=provider or "ollama")
    body = f"""
<h1>Generate proposal</h1>
<p class="muted">
A local model turns source text into a pending proposal. It cannot approve or
write canonical data; review the dry-run first. Set <code>STORYGRAM_LLM_API_KEY</code>
in the server environment for providers that require a key.
</p>
{_errors_block(errors or [])}
<form method="post" action="/proposals/generate">
<textarea name="source" spellcheck="false"
 placeholder="Paste an interview, note or memory...">{_esc(source)}</textarea>
<p>
<label>Provider
<input name="provider" value="{_esc(config.provider)}" style="padding:6px"></label>
<label>Model
<input name="model" value="{_esc(config.model)}" style="padding:6px"></label>
<label>LLM URL
<input name="url" value="{_esc(config.base_url)}" style="padding:6px; width:20rem"></label>
</p>
<p>
  <button class="primary" type="submit">Generate pending proposal</button>
  <a class="button" href="/proposals">Cancel</a>
</p>
</form>
"""
    return _layout("Generate proposal", body)


def _status_is_open(status: Any) -> bool:
    return status in {"draft", "proposed", "under_review", "approved"}


def render_detail(root: Path, proposal_id: str, errors: list[str] | None = None) -> tuple[int, str]:
    path = proposals_mod.find_proposal(root, proposal_id, include_applied=True)
    if path is None:
        return 404, _layout("Not found", f"<h1>Not found</h1><p>{_esc(proposal_id)}</p>")
    data = proposals_mod._load_json(path)
    if data is None:
        return 500, _layout(
            "Invalid proposal", f"<h1>Invalid proposal</h1><p>{_esc(proposal_id)}</p>"
        )

    plan_html = ""
    if _status_is_open(data.get("status")):
        try:
            plan = proposals_mod.plan_apply(root, data)
            operations = "".join(
                f"<li>{_esc(item['op'])} {_esc(item['record_type'])} "
                f"{_esc(item.get('record_id') or item.get('target_id') or '')}</li>"
                for item in plan.preview
            )
            files = "".join(
                f"<li>{_esc(file)}</li>" for file in sorted(str(p) for p in plan.writes)
            )
            plan_html = f"""
<h2>Dry-run preview</h2>
<ul>{operations}</ul>
<p class="muted">Files</p><ul>{files}</ul>
<form method="post" action="/proposals/{quote(proposal_id, safe="")}/approve">
<button class="primary" name="commit" value="yes" type="submit">Approve and commit</button>
<button name="commit" value="no" type="submit">Approve without commit</button>
</form>
<form method="post" action="/proposals/{quote(proposal_id, safe="")}/reject">
<p>
<input name="reason" placeholder="Rejection reason (optional)"
       style="width:70%; padding:6px">
</p>
<button type="submit">Reject</button>
</form>
<form method="post" action="/proposals/{quote(proposal_id, safe="")}/withdraw">
<p>
<input name="reason" placeholder="Withdrawal reason (optional)"
       style="width:70%; padding:6px">
</p>
<button type="submit">Withdraw</button>
</form>
"""
        except proposals_mod.ProposalError as exc:
            plan_html = f"<h2>Dry-run preview</h2>{_errors_block(exc.errors)}"

    edit_link = ""
    if path.parent == proposals_mod.pending_dir(root) and _status_is_open(data.get("status")):
        edit_link = (
            f'<a class="button" href="/proposals/{quote(proposal_id, safe="")}/edit">'
            "Edit pending proposal</a> "
        )

    body = f"""
<h1>{_esc(data.get("id"))}</h1>
<p>
{_status_badge(data.get("status"))}
<span class="muted">{_esc(data.get("title") or "")}</span>
</p>
{_errors_block(errors or [])}
{plan_html}
<h2>Proposal JSON</h2>
<pre>{_esc(json.dumps(data, indent=2))}</pre>
<p>{edit_link}<a class="button" href="/proposals">Back</a></p>
"""
    return 200, _layout(str(data.get("id")), body)


class StorygramServer(ThreadingHTTPServer):
    daemon_threads = True
    archive_root: Path
    provider_factory: Callable[[ProviderConfig], Provider] | None = None


class StorygramHandler(BaseHTTPRequestHandler):
    server_version = "Storygram/0.1"

    @property
    def root(self) -> Path:
        return cast(StorygramServer, self.server).archive_root

    def log_message(self, fmt: str, *args: Any) -> None:
        print(f"[web] {self.address_string()} {fmt % args}")

    def _send(self, status: int, body: str, content_type: str = "text/html; charset=utf-8") -> None:
        encoded = body.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(encoded)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(encoded)

    def _redirect(self, location: str) -> None:
        self.send_response(303)
        self.send_header("Location", location)
        self.end_headers()

    def _send_json(
        self, status: int, payload: dict[str, Any], headers: dict[str, str] | None = None
    ) -> None:
        encoded = json.dumps(payload, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.send_header("Cache-Control", "no-store")
        for name, value in (headers or {}).items():
            self.send_header(name, value)
        self.end_headers()
        self.wfile.write(encoded)

    def _read_json(self, required: bool = True) -> dict[str, Any]:
        content_type = self.headers.get("Content-Type", "").split(";", 1)[0].strip().lower()
        length = int(self.headers.get("Content-Length", "0"))
        if length == 0 and not required:
            return {}
        if content_type != "application/json":
            raise APIRequestError(415, "Content-Type must be application/json")
        if length > MAX_BODY:
            raise APIRequestError(413, "request body too large")
        raw = self.rfile.read(length).decode("utf-8")
        try:
            data = json.loads(raw)
        except Exception as exc:
            raise APIRequestError(400, f"Invalid JSON: {exc}") from exc
        if not isinstance(data, dict):
            raise APIRequestError(400, "Request body must be a JSON object")
        return data

    def _api_error(self, status: int, message: str, headers: dict[str, str] | None = None) -> None:
        self._send_json(status, {"ok": False, "errors": [message]}, headers)

    def _api_list(self, query: dict[str, list[str]]) -> None:
        include_applied = (query.get("include_applied") or ["0"])[0].lower() in {
            "1",
            "true",
            "yes",
        }
        items = []
        for path, data in proposals_mod.list_proposals(self.root, include_applied=include_applied):
            items.append(
                {
                    "id": data.get("id"),
                    "status": data.get("status"),
                    "title": data.get("title"),
                    "updated_at": data.get("updated_at"),
                    "operation_count": len(data.get("operations") or []),
                    "applied": path.parent == proposals_mod.applied_dir(self.root),
                }
            )
        self._send_json(200, {"ok": True, "proposals": items})

    def _api_get(self, proposal_id: str) -> None:
        path = proposals_mod.find_proposal(self.root, proposal_id, include_applied=True)
        if path is None:
            self._api_error(404, f"proposal not found: {proposal_id}")
            return
        data = proposals_mod._load_json(path)
        if data is None:
            self._api_error(500, f"cannot read proposal: {proposal_id}")
            return
        applied = path.parent == proposals_mod.applied_dir(self.root)
        errors: list[str] = []
        preview: list[dict[str, Any]] = []
        files: list[str] = []
        if not applied:
            try:
                plan = proposals_mod.plan_apply(self.root, data)
                preview = plan.preview
                files = sorted(
                    str(item.relative_to(self.root))
                    for item in plan.writes
                    if item.is_relative_to(self.root)
                )
            except proposals_mod.ProposalError as exc:
                errors = exc.errors
        self._send_json(
            200,
            {
                "ok": True,
                "applied": applied,
                "proposal": data,
                "validation": {"ok": not errors, "errors": errors},
                "preview": preview,
                "files": files,
            },
        )

    def _api_create(self) -> None:
        try:
            data = self._read_json()
            proposals_mod.create_pending(self.root, data)
        except APIRequestError as exc:
            self._api_error(exc.status, exc.message)
            return
        except proposals_mod.ProposalConflictError as exc:
            self._api_error(409, "; ".join(exc.errors))
            return
        except proposals_mod.ProposalError as exc:
            self._api_error(400, "; ".join(exc.errors))
            return
        proposal_id = str(data["id"])
        location = f"/api/proposals/{quote(proposal_id, safe='')}"
        self._send_json(
            201, {"ok": True, "proposal": data, "location": location}, {"Location": location}
        )

    def _api_update(self, proposal_id: str) -> None:
        try:
            data = self._read_json()
            path = proposals_mod.update_pending(self.root, proposal_id, data)
        except APIRequestError as exc:
            self._api_error(exc.status, exc.message)
            return
        except proposals_mod.ProposalNotFoundError as exc:
            self._api_error(404, "; ".join(exc.errors))
            return
        except proposals_mod.ProposalConflictError as exc:
            self._api_error(409, "; ".join(exc.errors))
            return
        except proposals_mod.ProposalError as exc:
            self._api_error(400, "; ".join(exc.errors))
            return
        saved = proposals_mod._load_json(path) or data
        self._send_json(200, {"ok": True, "proposal": saved})

    def _api_generate(self) -> None:
        try:
            data = self._read_json()
            source = data.get("source", data.get("text"))
            if not isinstance(source, str) or not source.strip():
                raise APIRequestError(400, "source text is empty")
            provider_name = data.get("provider")
            model = data.get("model")
            base_url = data.get("url", data.get("ollama_url"))
            api_key = data.get("api_key")
            for value, name in (
                (provider_name, "provider"),
                (model, "model"),
                (base_url, "url"),
                (api_key, "api_key"),
            ):
                if value is not None and not isinstance(value, str):
                    raise APIRequestError(400, f"{name} must be a string")
            try:
                config = provider_config(provider_name, model, base_url, api_key)
            except LLMAdapterError as exc:
                raise APIRequestError(400, str(exc)) from exc
            factory = cast(StorygramServer, self.server).provider_factory
            provider = factory(config) if factory is not None else provider_from_config(config)
            proposal = LLMAdapter(provider).generate(self.root, source)
            save = data.get("save", True)
            if not isinstance(save, bool):
                raise APIRequestError(400, "save must be a boolean")
            path = save_pending(self.root, proposal) if save else None
        except APIRequestError as exc:
            self._api_error(exc.status, exc.message)
            return
        except LLMAdapterError as exc:
            self._api_error(502, str(exc))
            return
        proposal_id = str(proposal["id"])
        location = f"/api/proposals/{quote(proposal_id, safe='')}"
        payload: dict[str, Any] = {
            "ok": True,
            "saved": path is not None,
            "proposal": proposal,
            "location": location,
        }
        self._send_json(201 if path is not None else 200, payload)

    def _api_close(self, proposal_id: str, status: str) -> None:
        try:
            data = self._read_json(required=False)
            reason = data.get("reason")
            if reason is not None and not isinstance(reason, str):
                raise APIRequestError(400, "reason must be a string")
            if status == "rejected":
                result = proposals_mod.reject_proposal(self.root, proposal_id, reason)
            else:
                result = proposals_mod.withdraw_proposal(self.root, proposal_id, reason)
        except APIRequestError as exc:
            self._api_error(exc.status, exc.message)
            return
        except proposals_mod.ProposalNotFoundError as exc:
            self._api_error(404, "; ".join(exc.errors))
            return
        except proposals_mod.ProposalConflictError as exc:
            self._api_error(409, "; ".join(exc.errors))
            return
        except proposals_mod.ProposalError as exc:
            self._api_error(400, "; ".join(exc.errors))
            return
        self._send_json(200, result)

    def _handle_api(self, method: str, path: str, query: str) -> None:
        segments = [unquote(part) for part in path.strip("/").split("/") if part]
        if len(segments) < 2 or segments[0] != "api" or segments[1] != "proposals":
            self._api_error(404, "API route not found")
            return
        if len(segments) == 2:
            if method == "GET":
                self._api_list(parse_qs(query, keep_blank_values=True))
            elif method == "POST":
                self._api_create()
            else:
                self._api_error(405, "method not allowed", {"Allow": "GET, POST"})
            return
        if len(segments) == 3:
            if segments[2] == "generate":
                if method == "POST":
                    self._api_generate()
                else:
                    self._api_error(405, "method not allowed", {"Allow": "POST"})
                return
            proposal_id = segments[2]
            if not proposal_id.startswith("proposal:"):
                self._api_error(400, "proposal id must start with proposal:")
                return
            if method == "GET":
                self._api_get(proposal_id)
            elif method == "PUT":
                self._api_update(proposal_id)
            else:
                self._api_error(405, "method not allowed", {"Allow": "GET, PUT"})
            return
        if len(segments) == 4:
            proposal_id = segments[2]
            action = segments[3]
            if not proposal_id.startswith("proposal:"):
                self._api_error(400, "proposal id must start with proposal:")
                return
            if action not in {"reject", "withdraw"}:
                self._api_error(404, "API route not found")
                return
            if method != "POST":
                self._api_error(405, "method not allowed", {"Allow": "POST"})
                return
            self._api_close(proposal_id, "rejected" if action == "reject" else "withdrawn")
            return
        self._api_error(404, "API route not found")

    def _read_form(self) -> dict[str, list[str]]:
        length = int(self.headers.get("Content-Length", "0"))
        if length > MAX_BODY:
            raise ValueError("request body too large")
        raw = self.rfile.read(length).decode("utf-8")
        return parse_qs(raw, keep_blank_values=True)

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        path = unquote(parsed.path)
        if path.startswith("/api/"):
            self._handle_api("GET", path, parsed.query)
            return
        if path == "/":
            self._send(200, render_home(self.root))
            return
        if path == "/records":
            self._send(200, render_records(self.root, parsed.query))
            return
        if path.startswith("/records/"):
            record_id = path.removeprefix("/records/").strip("/")
            status, body = render_record_detail(self.root, record_id)
            self._send(status, body)
            return
        if path == "/timeline":
            status, body = render_timeline(self.root, parsed.query)
            self._send(status, body)
            return
        if path == "/genogram":
            status, body = render_genogram(self.root, parsed.query)
            self._send(status, body)
            return
        if path == "/proposals":
            self._send(200, render_list(self.root))
            return
        if path == "/proposals/new":
            self._send(200, _new_form())
            return
        if path == "/proposals/generate":
            self._send(200, render_generate_form())
            return
        if path.startswith("/proposals/") and path.endswith("/edit"):
            proposal_id = path.removeprefix("/proposals/").removesuffix("/edit").strip("/")
            pending = proposals_mod.find_proposal(self.root, proposal_id)
            if pending is None:
                applied = proposals_mod.find_applied_proposal(self.root, proposal_id)
                if applied is not None:
                    self._send(
                        409,
                        _layout(
                            "Cannot edit",
                            f"<h1>Cannot edit applied proposal</h1><p>{_esc(proposal_id)}</p>",
                        ),
                    )
                else:
                    self._send(
                        404, _layout("Not found", f"<h1>Not found</h1><p>{_esc(proposal_id)}</p>")
                    )
                return
            data = proposals_mod._load_json(pending)
            if data is None or not _status_is_open(data.get("status")):
                self._send(
                    409,
                    _layout(
                        "Cannot edit",
                        f"<h1>Proposal is not editable</h1><p>{_esc(proposal_id)}</p>",
                    ),
                )
                return
            self._send(200, _edit_form(proposal_id, json.dumps(data, indent=2)))
            return
        if path.startswith("/proposals/"):
            proposal_id = path.removeprefix("/proposals/").strip("/")
            status, body = render_detail(self.root, proposal_id)
            self._send(status, body)
            return
        self._send(404, _layout("Not found", "<h1>Not found</h1>"))

    def do_POST(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        path = unquote(parsed.path)
        if path.startswith("/api/"):
            self._handle_api("POST", path, parsed.query)
            return
        try:
            form = self._read_form()
        except ValueError as exc:
            self._send(413, _layout("Bad request", _errors_block([str(exc)])))
            return

        if path == "/proposals/generate":
            source = (form.get("source") or [""])[0]
            provider_name = (form.get("provider") or [""])[0].strip() or None
            model = (form.get("model") or [""])[0].strip() or None
            base_url = (form.get("url") or [""])[0].strip() or None
            base_url = base_url or (form.get("ollama_url") or [""])[0].strip() or None
            if not source.strip():
                self._send(
                    400,
                    render_generate_form(
                        source, ["Source text is empty"], model, base_url, provider_name
                    ),
                )
                return
            try:
                config = provider_config(provider_name, model, base_url)
            except LLMAdapterError as exc:
                self._send(
                    400,
                    render_generate_form(source, [str(exc)], model, base_url, provider_name),
                )
                return
            factory = cast(StorygramServer, self.server).provider_factory
            provider = factory(config) if factory is not None else provider_from_config(config)
            try:
                data = LLMAdapter(provider).generate(self.root, source)
                save_pending(self.root, data)
            except LLMAdapterError as exc:
                self._send(
                    502,
                    render_generate_form(
                        source, [str(exc)], config.model, config.base_url, config.provider
                    ),
                )
                return
            generated_id = str(data["id"])
            self._redirect(f"/proposals/{quote(generated_id, safe='')}")
            return

        if path.startswith("/proposals/") and path.endswith("/edit"):
            edit_id = path.removeprefix("/proposals/").removesuffix("/edit").strip("/")
            raw = (form.get("json") or [""])[0]
            try:
                data = json.loads(raw)
            except Exception as exc:
                self._send(400, _edit_form(edit_id, raw, [f"Invalid JSON: {exc}"]))
                return
            if not isinstance(data, dict):
                self._send(400, _edit_form(edit_id, raw, ["Proposal must be a JSON object"]))
                return
            try:
                proposals_mod.update_pending(self.root, edit_id, data)
            except proposals_mod.ProposalConflictError as exc:
                self._send(409, _edit_form(edit_id, raw, exc.errors))
                return
            except proposals_mod.ProposalError as exc:
                self._send(400, _edit_form(edit_id, raw, exc.errors))
                return
            self._redirect(f"/proposals/{quote(edit_id, safe='')}")
            return

        if path == "/proposals/new":
            raw = (form.get("json") or [""])[0]
            try:
                data = json.loads(raw)
            except Exception as exc:
                self._send(400, _new_form(raw, [f"Invalid JSON: {exc}"]))
                return
            if not isinstance(data, dict):
                self._send(400, _new_form(raw, ["Proposal must be a JSON object"]))
                return
            try:
                proposals_mod.create_pending(self.root, data)
            except proposals_mod.ProposalError as exc:
                self._send(400, _new_form(raw, exc.errors))
                return
            proposal_id = str(data["id"])
            self._redirect(f"/proposals/{quote(proposal_id, safe='')}")
            return

        if path.startswith("/proposals/") and path.endswith("/approve"):
            proposal_id = path.removeprefix("/proposals/").removesuffix("/approve").strip("/")
            commit = (form.get("commit") or ["yes"])[0] != "no"
            try:
                proposals_mod.apply_proposal(self.root, proposal_id, commit=commit)
            except proposals_mod.ProposalError as exc:
                status, body = render_detail(self.root, proposal_id, exc.errors)
                self._send(400, body)
                return
            self._redirect(f"/proposals/{quote(proposal_id, safe='')}")
            return

        if path.startswith("/proposals/") and path.endswith("/reject"):
            proposal_id = path.removeprefix("/proposals/").removesuffix("/reject").strip("/")
            reason = (form.get("reason") or [""])[0] or None
            try:
                proposals_mod.reject_proposal(self.root, proposal_id, reason)
            except proposals_mod.ProposalError as exc:
                status, body = render_detail(self.root, proposal_id, exc.errors)
                self._send(400, body)
                return
            self._redirect(f"/proposals/{quote(proposal_id, safe='')}")
            return

        if path.startswith("/proposals/") and path.endswith("/withdraw"):
            proposal_id = path.removeprefix("/proposals/").removesuffix("/withdraw").strip("/")
            reason = (form.get("reason") or [""])[0] or None
            try:
                proposals_mod.withdraw_proposal(self.root, proposal_id, reason)
            except proposals_mod.ProposalError as exc:
                status, body = render_detail(self.root, proposal_id, exc.errors)
                self._send(400, body)
                return
            self._redirect(f"/proposals/{quote(proposal_id, safe='')}")
            return

        self._send(404, _layout("Not found", "<h1>Not found</h1>"))

    def do_PUT(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        path = unquote(parsed.path)
        if path.startswith("/api/"):
            self._handle_api("PUT", path, parsed.query)
            return
        self._send(405, _layout("Method not allowed", "<h1>Method not allowed</h1>"))


def create_server(
    root: Path,
    host: str = "0.0.0.0",
    port: int = 8080,
    provider_factory: Callable[[ProviderConfig], Provider] | None = None,
) -> StorygramServer:
    server = StorygramServer((host, port), StorygramHandler)
    server.archive_root = Path(root)
    server.provider_factory = provider_factory
    return server


def serve(root: Path, host: str = "0.0.0.0", port: int = 8080) -> None:
    server = create_server(root, host, port)
    print(f"Storygram web UI: http://{host}:{server.server_port}/")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
