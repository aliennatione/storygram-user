"""Minimal local web UI for proposal review."""

from __future__ import annotations

import html
import json
import re
import unicodedata
from collections.abc import Callable
from datetime import UTC, datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, cast
from urllib.parse import parse_qs, quote, unquote, urlencode, urlparse, urlsplit, urlunsplit
from uuid import uuid4

from . import export as export_mod
from . import proposals as proposals_mod
from . import validate as validate_mod
from .conflicts import list_conflicts
from .genogram import FAMILY_PREDICATES, build_genogram
from .i18n import (
    current_language,
    current_path,
    normalize_language,
    set_language,
    set_path,
)
from .i18n import (
    t as _t,
)
from .llm import (
    LLMAdapter,
    LLMAdapterError,
    Provider,
    ProviderConfig,
    provider_config,
    provider_from_config,
    review_proposal,
    save_pending,
)
from .media import list_media
from .registry import RECORD_TYPES, TYPE_BY_NAME, iter_reference_strings
from .timeline import build_timeline

MAX_BODY = 4 * 1024 * 1024
MEMORY_EPISODE_TYPES = (
    "memory",
    "interview",
    "letter",
    "photograph",
    "audio",
    "video",
    "document",
    "observation",
    "other",
)
VISIBILITIES = ("private", "restricted", "family", "public")
ENTITY_TYPES = {
    "Place": "place",
    "Event": "event",
    "Organization": "organization",
    "Period": "period",
    "Collection": "collection",
}
ANNOTATION_TARGET_TYPES = (
    "Episode",
    "Assertion",
    "Person",
    "Organization",
    "Place",
    "Period",
    "Event",
    "Relationship",
    "Source",
    "MediaAsset",
    "Annotation",
    "Narrative",
    "Collection",
    "Conflict",
)
ASSERTION_ENTITY_TYPES = (
    "Person",
    "Organization",
    "Place",
    "Period",
    "Event",
    "Relationship",
    "Source",
    "Episode",
    "Collection",
    "Narrative",
    "Annotation",
    "MediaAsset",
)
ASSERTION_PREDICATES = (
    "relation:parent",
    "relation:child",
    "relation:spouse",
    "relation:sibling",
    "relation:partner",
    "relation:lived_in",
    "relation:born_in",
    "relation:died_in",
    "relation:worked_as",
    "relation:moved_to",
    "relation:member_of",
    "relation:documented_in",
    "relation:friend",
)
ASSERTION_STATUSES = ("draft", "proposed", "reported", "confirmed", "disputed", "rejected")
CONFLICT_STATUSES = ("open", "under_review", "resolved", "accepted_as_plural", "rejected")
SOURCE_TYPES = (
    "oral",
    "written",
    "archival",
    "registry",
    "photograph",
    "audio",
    "video",
    "website",
    "other",
)
EXPORT_FORMATS = {
    "json": ("application/json; charset=utf-8", "storygram-export.json"),
    "jsonld": ("application/ld+json; charset=utf-8", "storygram-export.jsonld"),
    "yaml": ("application/yaml; charset=utf-8", "storygram-export.yaml"),
    "markdown": ("text/markdown; charset=utf-8", "storygram-export.md"),
}
EXPORT_LABELS = {"json": "JSON", "jsonld": "JSON-LD", "yaml": "YAML", "markdown": "Markdown"}


class APIRequestError(Exception):
    def __init__(self, status: int, message: str):
        self.status = status
        self.message = message
        super().__init__(message)


def _esc(value: Any) -> str:
    return html.escape(str(value), quote=True)


def _layout(title: str, body: str) -> str:
    lang = current_language()
    next_path = quote(current_path(), safe="")
    en_attr = ' aria-current="true"' if lang == "en" else ""
    it_attr = ' aria-current="true"' if lang == "it" else ""
    language_links = (
        f'<a href="/lang/en?next={next_path}"{en_attr}>EN</a>'
        f'<a href="/lang/it?next={next_path}"{it_attr}>IT</a>'
    )
    return f"""<!doctype html>
<html lang="{lang}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{_esc(title)} - Storygram</title>

<style>
:root {{ --bg:#0f172a; --card:#111827; --text:#e5e7eb; --muted:#94a3b8; --accent:#22c55e; --line:#1f2937; }}
body {{ font-family:Inter,system-ui,sans-serif; }}
@media (prefers-color-scheme: dark) {{ body {{ background:linear-gradient(135deg,#0f172a,#111827); color:#e5e7eb; }} }}
header {{ background:#111827cc; backdrop-filter:blur(8px); border-bottom:1px solid var(--line); }}
main {{ max-width:1200px; }}
.card {{ background:var(--card); border:1px solid var(--line); border-radius:14px; padding:20px; box-shadow:0 10px 30px #0005; }}
table {{ background:#111827; border-radius:10px; overflow:hidden; }}
th {{ background:#1f2937; }}
button, .button {{ background:var(--accent); color:#052e16; border:none; border-radius:8px; padding:8px 14px; font-weight:600; }}
.error {{ background:#7f1d1d; color:#fecaca; border-left:4px solid #ef4444; }}
.ok {{ background:#14532d; color:#bbf7d0; border-left:4px solid #22c55e; }}
body { max-width: 100%; }
main { padding: 2rem; }
header { position: sticky; top: 0; z-index: 10; }
nav a { padding: 6px 10px; border-radius: 8px; transition: background .2s; }
nav a:hover { background: #ffffff20; }
.card, .panel { background: #ffffff10; border: 1px solid #ffffff20; border-radius: 16px; padding: 1.25rem; margin: 1rem 0; backdrop-filter: blur(6px); }
table { border-radius: 12px; overflow: hidden; }
th, td { padding: 12px; }
button, .button { transition: transform .1s, opacity .2s; }
button:hover, .button:hover { transform: translateY(-1px); opacity: .9; }
form input, form select, textarea { border-radius: 10px; padding: 10px; }
:root {{ color-scheme: light dark; --line:#d0d7de; --muted:#57606a; --accent:#0969da; }}
* {{ box-sizing: border-box; }}
body {{ margin:0; font-family: system-ui, sans-serif; line-height:1.45; }}
header {{
  border-bottom:1px solid var(--line); padding:12px 24px;
  display:flex; gap:20px; align-items:center; flex-wrap:wrap;
}}
header strong {{ font-size:1.1rem; }}
nav a {{ margin-right:14px; color:var(--accent); text-decoration:none; }}
nav a[aria-current="true"] {{ font-weight:700; text-decoration:underline; }}
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
form label {{ display:block; margin:10px 0; }}
form input, form select {{
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
    <a href="/">{_t("Home")}</a><a href="/records">{_t("Records")}</a>
    <a href="/timeline">{_t("Timeline")}</a>
    <a href="/genogram">{_t("Genogram")}</a>
    <a href="/conflicts">{_t("Conflicts")}</a>
    <a href="/proposals">{_t("Proposals")}</a>
    <a href="/memories/new">{_t("Add memory")}</a>
    <a href="/sources/new">{_t("Add source")}</a>
    <a href="/people/new">{_t("Add person")}</a>
    <a href="/entities/new">{_t("Add entity")}</a>
    <a href="/relationships/new">{_t("Add relationship")}</a>
    <a href="/assertions/new">{_t("Add assertion")}</a>
    <a href="/annotations/new">{_t("Add annotation")}</a>
    <a href="/narratives/new">{_t("Add narrative")}</a>
    <a href="/conflicts/new">{_t("Add conflict")}</a>
    <a href="/media-assets/new">{_t("Add media asset")}</a>
    <a href="/media">{_t("Media")}</a>
    <a href="/proposals/new">{_t("New proposal")}</a>
    <a href="/proposals/generate">{_t("Generate")}</a>
  </nav>
  <nav>{language_links}</nav>
</header>
<main>{body}</main>
</body>
</html>"""


def _errors_block(errors: list[str]) -> str:
    if not errors:
        return ""
    items = "".join(f"<li>{_esc(error)}</li>" for error in errors)
    return f'<div class="error"><strong>{_t("Could not continue")}</strong><ul>{items}</ul></div>'


def _status_badge(status: Any) -> str:
    label = _t(str(status)) if status else _t("unknown")
    return f'<span class="badge">{_esc(label)}</span>'


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
    return _notice_block(_t("Some records could not be loaded"), items)


def _record_links(ids: list[str], known_ids: set[str]) -> str:
    if not ids:
        return f'<p class="muted">{_t("None.")}</p>'
    items = []
    for record_id in ids:
        if record_id in known_ids:
            href = _record_href(record_id)
            items.append(f'<li><a href="{_esc(href)}">{_esc(record_id)}</a></li>')
        else:
            items.append(f'<li><span class="muted">{_esc(record_id)} {_t("(missing)")}</span></li>')
    return f"<ul>{''.join(items)}</ul>"


def _related_proposals_html(items: list[tuple[str, str, str]]) -> str:
    if not items:
        return f'<p class="muted">{_t("No proposal touches this record yet.")}</p>'
    rows = "".join(
        f'<li><a href="/proposals/{quote(proposal_id, safe="")}">{_esc(proposal_id)}</a> '
        f"{_status_badge(status)} "
        f'<span class="muted">{_esc(title)}</span></li>'
        for proposal_id, status, title in items
    )
    return f"<ul>{rows}</ul>"


def _known_ids(records: list[tuple[Path, dict[str, Any]]]) -> set[str]:
    return {str(data["id"]) for _, data in records if isinstance(data.get("id"), str)}


def _evidence_records(root: Path) -> list[tuple[str, str, str]]:
    records, _ = validate_mod.load_records(root)
    evidence = []
    for _, data in records:
        record_id = data.get("id")
        record_type = data.get("type")
        if not isinstance(record_id, str) or record_type not in {"Episode", "Source", "Annotation"}:
            continue
        evidence.append((record_id, str(record_type), _record_name(data)))
    return sorted(evidence, key=lambda item: (item[1], item[0]))


def _person_records(root: Path) -> list[tuple[str, str]]:
    records, _ = validate_mod.load_records(root)
    people = []
    for _, data in records:
        record_id = data.get("id")
        if (
            not isinstance(record_id, str)
            or data.get("type") != "Person"
            or data.get("status") in {"archived", "rejected"}
        ):
            continue
        people.append((record_id, _record_name(data)))
    return sorted(people, key=lambda item: (item[1].casefold(), item[0]))


def _evidence_fieldset(root: Path, selected_evidence: list[str] | None) -> str:
    selected = set(selected_evidence or [])
    evidence_records = _evidence_records(root)
    if not evidence_records:
        return f'<p class="warning">{_t("Add a memory or source before adding this record.")}</p>'
    options = "".join(
        f'<label class="checkbox"><input type="checkbox" name="evidence" '
        f'value="{_esc(record_id)}"{" checked" if record_id in selected else ""}> '
        f"{_esc(record_type)} · {_esc(record_id)}"
        f"{' · ' + _esc(name) if name else ''}</label>"
        for record_id, record_type, name in evidence_records
    )
    return f"<fieldset><legend>{_t('Evidence')}</legend>{options}</fieldset>"


def _record_link(record_id: Any, known_ids: set[str]) -> str:
    if not isinstance(record_id, str) or not record_id:
        return '<span class="muted">—</span>'
    if record_id in known_ids:
        href = _record_href(record_id)
        return f'<a href="{_esc(href)}">{_esc(record_id)}</a>'
    return f'<span class="muted">{_esc(record_id)} {_t("(missing)")}</span>'


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
        return f'<p class="muted">{_t("No proposals yet.")}</p>'
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
        f"<table><thead><tr><th>{_t('ID')}</th><th>{_t('Status')}</th>"
        f"<th>{_t('Title')}</th><th>{_t('Operations')}</th>"
        f"<th>{_t('Location')}</th></tr></thead><tbody>" + "".join(rows) + "</tbody></table>"
    )


def render_home(root: Path) -> str:
    result = validate_mod.validate_archive(root)
    records, load_errors = validate_mod.load_records(root)
    pending = proposals_mod.list_proposals(root, include_applied=False)
    applied = proposals_mod.list_proposals(root, include_applied=True)
    applied = [(path, data) for path, data in applied if data.get("status") == "merged"]
    status = f'<div class="ok">{_t("Archive validates.")}</div>'
    if not result["ok"]:
        status = _errors_block(load_errors + result["errors"])
    counts = []
    for record_type in RECORD_TYPES:
        count = sum(1 for _, data in records if data.get("type") == record_type.name)
        counts.append(f"<li>{_esc(record_type.name)}: {count}</li>")
    body = f"""
<h1>Storygram</h1>
<p class="muted">{_t("Local-first review surface. Canonical changes require approval.")}</p>
<div class="card" style="margin:16px 0;">
<h2>{_t("Start here")}</h2>
<p>{_t("Paste a memory or interview and let AI create a reviewable proposal.")}</p>
<a class="button primary" href="/proposals/generate">{_t("Generate with AI")}</a>
</div>
{status}
<h2>{_t("Review queue")}</h2>
<table><thead><tr><th>{_t("Pending")}</th><th>{_t("Merged")}</th>
<th>{_t("Records")}</th></tr></thead>
<tbody><tr><td>{len(pending)}</td><td>{len(applied)}</td><td>{len(records)}</td></tr></tbody></table>
<p>
  <a class="button" href="/records">{_t("Browse records")}</a>
  <a class="button" href="/timeline">{_t("Timeline")}</a>
  <a class="button" href="/genogram">{_t("Genogram")}</a>
  <a class="button" href="/conflicts">{_t("Conflicts")}</a>
  <a class="button primary" href="/memories/new">{_t("Add memory")}</a>
  <a class="button" href="/sources/new">{_t("Add source")}</a>
  <a class="button" href="/people/new">{_t("Add person")}</a>
  <a class="button" href="/entities/new">{_t("Add entity")}</a>
  <a class="button" href="/relationships/new">{_t("Add relationship")}</a>
  <a class="button" href="/assertions/new">{_t("Add assertion")}</a>
  <a class="button" href="/annotations/new">{_t("Add annotation")}</a>
  <a class="button" href="/narratives/new">{_t("Add narrative")}</a>
  <a class="button" href="/conflicts/new">{_t("Add conflict")}</a>
  <a class="button" href="/media-assets/new">{_t("Add media asset")}</a>
  <a class="button" href="/media">{_t("Media")}</a>
  <a class="button" href="/proposals/new">{_t("Create proposal")}</a>
  <a class="button" href="/proposals/generate">{_t("Generate with Ollama")}</a>
  <a class="button" href="/proposals">{_t("View proposals")}</a>
</p>
<h2>{_t("Record counts")}</h2><ul>{"".join(counts)}</ul>
"""
    return _layout(_t("Home"), body)


def _split_csv(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def _memory_proposal(root: Path, values: dict[str, str]) -> tuple[dict[str, Any] | None, list[str]]:
    text = values.get("text", "").strip()
    title = values.get("title", "").strip()
    episode_type = values.get("episode_type", "").strip() or "memory"
    captured_at = values.get("captured_at", "").strip()
    participants = list(dict.fromkeys(_split_csv(values.get("participants", ""))))
    tags = list(dict.fromkeys(_split_csv(values.get("tags", ""))))
    visibility = values.get("visibility", "").strip()

    errors: list[str] = []
    if not text:
        errors.append(_t("Memory text is required"))
    if episode_type not in MEMORY_EPISODE_TYPES:
        errors.append(_t("Unsupported episode type: {value}", value=episode_type))
    if visibility and visibility not in VISIBILITIES:
        errors.append(_t("Unsupported visibility: {value}", value=visibility))

    records, _ = validate_mod.load_records(root)
    known_ids = _known_ids(records)
    for participant in participants:
        if participant not in known_ids:
            errors.append(_t("Unknown participant: {value}", value=participant))
    if errors:
        return None, errors

    now = datetime.now(UTC).isoformat()
    token = uuid4().hex[:12]
    record: dict[str, Any] = {
        "id": f"episode:memory-{token}",
        "type": "Episode",
        "episode_type": episode_type,
        "status": "reported",
        "created_at": now,
        "updated_at": now,
        "content": {"text": text},
    }
    if title:
        record["title"] = title
    if captured_at:
        record["captured_at"] = captured_at
    if participants:
        record["participants"] = participants
    if tags:
        record["tags"] = tags
    if visibility:
        record["visibility"] = visibility

    record_errors = validate_mod.validate_instance(root, record, TYPE_BY_NAME["Episode"])
    if record_errors:
        return None, record_errors

    proposal_title = title or text.splitlines()[0][:80] or _t("Memory capture")
    proposal = {
        "id": f"proposal:memory-{token}",
        "type": "Proposal",
        "status": "proposed",
        "created_at": now,
        "updated_at": now,
        "title": proposal_title,
        "rationale": _t("Created from the Add memory form."),
        "operations": [{"op": "create", "record_type": "Episode", "record": record}],
    }
    return proposal, []


def _entity_proposal(
    root: Path, values: dict[str, str], evidence: list[str]
) -> tuple[dict[str, Any] | None, list[str]]:
    entity_type = values.get("entity_type", "").strip() or "Place"
    name = values.get("name", "").strip()
    notes = values.get("notes", "").strip()
    visibility = values.get("visibility", "").strip()
    evidence = list(dict.fromkeys(item for item in evidence if item))

    errors: list[str] = []
    if entity_type not in ENTITY_TYPES:
        errors.append(_t("Unsupported entity type: {value}", value=entity_type))
    if not name:
        errors.append(_t("Name is required"))
    if visibility and visibility not in VISIBILITIES:
        errors.append(_t("Unsupported visibility: {value}", value=visibility))
    known_evidence = {record_id for record_id, _, _ in _evidence_records(root)}
    if not evidence:
        errors.append(_t("Evidence is required"))
    for record_id in evidence:
        if record_id not in known_evidence:
            errors.append(_t("Unknown evidence: {value}", value=record_id))
    if errors:
        return None, errors

    now = datetime.now(UTC).isoformat()
    token = uuid4().hex[:12]
    record: dict[str, Any] = {
        "id": f"{ENTITY_TYPES[entity_type]}:{_slug(name)}-{token}",
        "type": entity_type,
        "name": name,
        "status": "reported",
        "created_at": now,
        "updated_at": now,
    }
    if notes:
        record["notes"] = notes
    if visibility:
        record["visibility"] = visibility

    record_errors = validate_mod.validate_instance(root, record, TYPE_BY_NAME[entity_type])
    if record_errors:
        return None, record_errors

    proposal = {
        "id": f"proposal:entity-{token}",
        "type": "Proposal",
        "status": "proposed",
        "created_at": now,
        "updated_at": now,
        "title": _t("New {type}: {name}", type=_t(entity_type), name=name),
        "rationale": _t("Created from the Add entity form."),
        "operations": [
            {
                "op": "create",
                "record_type": entity_type,
                "record": record,
                "evidence": evidence,
            }
        ],
    }
    return proposal, []


def render_entity_form(
    root: Path,
    values: dict[str, str] | None = None,
    errors: list[str] | None = None,
    selected_evidence: list[str] | None = None,
) -> str:
    values = values or {}
    entity_type = values.get("entity_type") or "Place"
    visibility = values.get("visibility") or ""
    notes_value = _esc(values.get("notes", ""))
    type_options = "".join(
        f'<option value="{_esc(item)}"'
        f"{' selected' if item == entity_type else ''}>{_esc(_t(item))}</option>"
        for item in ENTITY_TYPES
    )
    visibility_options = "".join(
        f'<option value="{_esc(item)}"'
        f"{' selected' if item == visibility else ''}>{_esc(_t(item))}</option>"
        for item in VISIBILITIES
    )
    evidence_block = _evidence_fieldset(root, selected_evidence)
    intro = _t(
        "Add a place, event, organization or period as a pending proposal. It needs "
        "existing evidence and enters canonical data only after approval."
    )
    body = f"""
<h1>{_t("Add entity")}</h1>
<p class="muted">
{intro}
</p>
{_errors_block(errors or [])}
<form method="post" action="/entities/new">
<p>
<label>{_t("Record type")}
  <select name="entity_type">{type_options}</select>
</label>
<label>{_t("Visibility")}
  <select name="visibility">
    <option value="">{_t("Unspecified")}</option>{visibility_options}
  </select>
</label>
</p>
<label>{_t("Name")}
  <input name="name" value="{_esc(values.get("name", ""))}" required style="width:100%">
</label>
<label>{_t("Notes")}
  <textarea name="notes" spellcheck="true"
    placeholder="{_t("Optional notes about this record")}">{notes_value}</textarea>
</label>
{evidence_block}
<p>
  <button class="primary" type="submit">{_t("Save pending proposal")}</button>
  <a class="button" href="/proposals/new">{_t("Advanced JSON editor")}</a>
  <a class="button" href="/proposals">{_t("Cancel")}</a>
</p>
</form>
"""
    return _layout(_t("Add entity"), body)


def _source_proposal(root: Path, values: dict[str, str]) -> tuple[dict[str, Any] | None, list[str]]:
    title = values.get("title", "").strip()
    source_type = values.get("source_type", "").strip()
    visibility = values.get("visibility", "").strip()
    notes = values.get("notes", "").strip()

    errors: list[str] = []
    if not title:
        errors.append(_t("Title is required"))
    if source_type and source_type not in SOURCE_TYPES:
        errors.append(_t("Unsupported source type: {value}", value=source_type))
    if visibility and visibility not in VISIBILITIES:
        errors.append(_t("Unsupported visibility: {value}", value=visibility))
    if errors:
        return None, errors

    now = datetime.now(UTC).isoformat()
    token = uuid4().hex[:12]
    record: dict[str, Any] = {
        "id": f"source:{_slug(title)}-{token}",
        "type": "Source",
        "title": title,
        "status": "reported",
        "created_at": now,
        "updated_at": now,
    }
    if source_type:
        record["source_type"] = source_type
    if visibility:
        record["visibility"] = visibility
    if notes:
        record["notes"] = notes

    record_errors = validate_mod.validate_instance(root, record, TYPE_BY_NAME["Source"])
    if record_errors:
        return None, record_errors

    proposal = {
        "id": f"proposal:source-{token}",
        "type": "Proposal",
        "status": "proposed",
        "created_at": now,
        "updated_at": now,
        "title": _t("New source: {title}", title=title),
        "rationale": _t("Created from the Add source form."),
        "operations": [{"op": "create", "record_type": "Source", "record": record}],
    }
    return proposal, []


def render_source_form(
    values: dict[str, str] | None = None, errors: list[str] | None = None
) -> str:
    values = values or {}
    source_type = values.get("source_type") or ""
    visibility = values.get("visibility") or ""
    notes_value = _esc(values.get("notes", ""))
    source_type_options = "".join(
        f'<option value="{_esc(item)}"'
        f"{' selected' if item == source_type else ''}>{_esc(_t(item))}</option>"
        for item in SOURCE_TYPES
    )
    visibility_options = "".join(
        f'<option value="{_esc(item)}"'
        f"{' selected' if item == visibility else ''}>{_esc(_t(item))}</option>"
        for item in VISIBILITIES
    )
    intro = _t(
        "Add a source as a pending proposal. A source can support later people, "
        "relationships and assertions; it enters canonical data only after approval."
    )
    body = f"""
<h1>{_t("Add source")}</h1>
<p class="muted">
{intro}
</p>
{_errors_block(errors or [])}
<form method="post" action="/sources/new">
<label>{_t("Title")}
  <input name="title" value="{_esc(values.get("title", ""))}" required style="width:100%">
</label>
<p>
<label>{_t("Source type")}
  <select name="source_type">
    <option value="">{_t("Unspecified")}</option>{source_type_options}
  </select>
</label>
<label>{_t("Visibility")}
  <select name="visibility">
    <option value="">{_t("Unspecified")}</option>{visibility_options}
  </select>
</label>
</p>
<label>{_t("Notes")}
  <textarea name="notes" spellcheck="true"
    placeholder="{_t("Optional notes about this source")}">{notes_value}</textarea>
</label>
<p>
  <button class="primary" type="submit">{_t("Save pending proposal")}</button>
  <a class="button" href="/proposals/new">{_t("Advanced JSON editor")}</a>
  <a class="button" href="/proposals">{_t("Cancel")}</a>
</p>
</form>
"""
    return _layout(_t("Add source"), body)


def _slug(value: str) -> str:
    ascii_value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode()
    slug = re.sub(r"[^a-z0-9]+", "-", ascii_value.casefold()).strip("-")
    return slug[:40] or "person"


def _person_proposal(
    root: Path, values: dict[str, str], evidence: list[str]
) -> tuple[dict[str, Any] | None, list[str]]:
    name = values.get("name", "").strip()
    notes = values.get("notes", "").strip()
    visibility = values.get("visibility", "").strip()
    evidence = list(dict.fromkeys(item for item in evidence if item))

    errors: list[str] = []
    if not name:
        errors.append(_t("Name is required"))
    if visibility and visibility not in VISIBILITIES:
        errors.append(_t("Unsupported visibility: {value}", value=visibility))
    known_evidence = {record_id for record_id, _, _ in _evidence_records(root)}
    if not evidence:
        errors.append(_t("Evidence is required"))
    for record_id in evidence:
        if record_id not in known_evidence:
            errors.append(_t("Unknown evidence: {value}", value=record_id))
    if errors:
        return None, errors

    now = datetime.now(UTC).isoformat()
    token = uuid4().hex[:12]
    record: dict[str, Any] = {
        "id": f"person:{_slug(name)}-{token}",
        "type": "Person",
        "name": name,
        "status": "reported",
        "created_at": now,
        "updated_at": now,
    }
    if notes:
        record["notes"] = notes
    if visibility:
        record["visibility"] = visibility

    record_errors = validate_mod.validate_instance(root, record, TYPE_BY_NAME["Person"])
    if record_errors:
        return None, record_errors

    proposal = {
        "id": f"proposal:person-{token}",
        "type": "Proposal",
        "status": "proposed",
        "created_at": now,
        "updated_at": now,
        "title": _t("New person: {name}", name=name),
        "rationale": _t("Created from the Add person form."),
        "operations": [
            {
                "op": "create",
                "record_type": "Person",
                "record": record,
                "evidence": evidence,
            }
        ],
    }
    return proposal, []


def render_person_form(
    root: Path,
    values: dict[str, str] | None = None,
    errors: list[str] | None = None,
    selected_evidence: list[str] | None = None,
) -> str:
    values = values or {}
    visibility = values.get("visibility") or ""
    notes_value = _esc(values.get("notes", ""))
    evidence_block = _evidence_fieldset(root, selected_evidence)
    visibility_options = "".join(
        f'<option value="{_esc(item)}"'
        f"{' selected' if item == visibility else ''}>{_esc(_t(item))}</option>"
        for item in VISIBILITIES
    )
    intro = _t(
        "Add a person as a pending proposal. The person enters canonical data only "
        "after a human approves the proposal."
    )
    body = f"""
<h1>{_t("Add person")}</h1>
<p class="muted">
{intro}
</p>
{_errors_block(errors or [])}
<form method="post" action="/people/new">
<label>{_t("Name")}
  <input name="name" value="{_esc(values.get("name", ""))}" required style="width:100%">
</label>
<p>
<label>{_t("Visibility")}
  <select name="visibility">
    <option value="">{_t("Unspecified")}</option>{visibility_options}
  </select>
</label>
</p>
<label>{_t("Notes")}
  <textarea name="notes" spellcheck="true"
    placeholder="{_t("Optional notes about this person")}">{notes_value}</textarea>
</label>
{evidence_block}
<p>
  <button class="primary" type="submit">{_t("Save pending proposal")}</button>
  <a class="button" href="/proposals/new">{_t("Advanced JSON editor")}</a>
  <a class="button" href="/proposals">{_t("Cancel")}</a>
</p>
</form>
"""
    return _layout(_t("Add person"), body)


def _relationship_proposal(
    root: Path, values: dict[str, str], evidence: list[str]
) -> tuple[dict[str, Any] | None, list[str]]:
    subject = values.get("subject", "").strip()
    predicate = values.get("predicate", "").strip()
    object_id = values.get("object", "").strip()
    start = values.get("start", "").strip()
    end = values.get("end", "").strip()
    precision = values.get("precision", "").strip()
    visibility = values.get("visibility", "").strip()
    notes = values.get("notes", "").strip()
    evidence = list(dict.fromkeys(item for item in evidence if item))

    people = {record_id for record_id, _ in _person_records(root)}
    errors: list[str] = []
    if not subject:
        errors.append(_t("Subject is required"))
    elif subject not in people:
        errors.append(_t("Unknown person: {value}", value=subject))
    if not object_id:
        errors.append(_t("Object is required"))
    elif object_id not in people:
        errors.append(_t("Unknown person: {value}", value=object_id))
    if subject and subject == object_id:
        errors.append(_t("Subject and object must be different"))
    if predicate not in FAMILY_PREDICATES:
        errors.append(_t("Unsupported predicate: {value}", value=predicate))
    if visibility and visibility not in VISIBILITIES:
        errors.append(_t("Unsupported visibility: {value}", value=visibility))
    known_evidence = {record_id for record_id, _, _ in _evidence_records(root)}
    if not evidence:
        errors.append(_t("Evidence is required"))
    for record_id in evidence:
        if record_id not in known_evidence:
            errors.append(_t("Unknown evidence: {value}", value=record_id))
    if errors:
        return None, errors

    now = datetime.now(UTC).isoformat()
    token = uuid4().hex[:12]
    record: dict[str, Any] = {
        "id": f"relationship:{token}",
        "type": "Relationship",
        "subject": subject,
        "predicate": predicate,
        "object": object_id,
        "status": "reported",
        "created_at": now,
        "updated_at": now,
    }
    valid_time = {}
    if start:
        valid_time["start"] = start
    if end:
        valid_time["end"] = end
    if precision:
        valid_time["precision"] = precision
    if valid_time:
        record["valid_time"] = valid_time
    if visibility:
        record["visibility"] = visibility
    if notes:
        record["notes"] = notes

    record_errors = validate_mod.validate_instance(root, record, TYPE_BY_NAME["Relationship"])
    if record_errors:
        return None, record_errors

    people_by_id = dict(_person_records(root))
    proposal = {
        "id": f"proposal:relationship-{token}",
        "type": "Proposal",
        "status": "proposed",
        "created_at": now,
        "updated_at": now,
        "title": _t(
            "New relationship: {subject} → {object}",
            subject=people_by_id.get(subject, subject),
            object=people_by_id.get(object_id, object_id),
        ),
        "rationale": _t("Created from the Add relationship form."),
        "operations": [
            {
                "op": "create",
                "record_type": "Relationship",
                "record": record,
                "evidence": evidence,
            }
        ],
    }
    return proposal, []


def render_relationship_form(
    root: Path,
    values: dict[str, str] | None = None,
    errors: list[str] | None = None,
    selected_evidence: list[str] | None = None,
) -> str:
    values = values or {}
    subject = values.get("subject") or ""
    predicate = values.get("predicate") or ""
    object_id = values.get("object") or ""
    precision = values.get("precision") or ""
    visibility = values.get("visibility") or ""
    notes_value = _esc(values.get("notes", ""))
    people = _person_records(root)
    warning = ""
    if len(people) < 2:
        warning = (
            f'<p class="warning">{_t("Add at least two people before adding a relationship.")}</p>'
        )
    subject_options = f'<option value="">{_t("Choose a person")}</option>' + "".join(
        f'<option value="{_esc(record_id)}"'
        f"{' selected' if record_id == subject else ''}>"
        f"{_esc(name or record_id)} · {_esc(record_id)}</option>"
        for record_id, name in people
    )
    object_options = f'<option value="">{_t("Choose a person")}</option>' + "".join(
        f'<option value="{_esc(record_id)}"'
        f"{' selected' if record_id == object_id else ''}>"
        f"{_esc(name or record_id)} · {_esc(record_id)}</option>"
        for record_id, name in people
    )
    predicate_options = "".join(
        f'<option value="{_esc(item)}"'
        f"{' selected' if item == predicate else ''}>{_esc(item)}</option>"
        for item in sorted(FAMILY_PREDICATES)
    )
    precision_options = "".join(
        f'<option value="{_esc(item)}"'
        f"{' selected' if item == precision else ''}>{_esc(_t(item))}</option>"
        for item in ("day", "month", "year", "decade", "approximate", "unknown")
    )
    visibility_options = "".join(
        f'<option value="{_esc(item)}"'
        f"{' selected' if item == visibility else ''}>{_esc(_t(item))}</option>"
        for item in VISIBILITIES
    )
    evidence_block = _evidence_fieldset(root, selected_evidence)
    intro = _t(
        "Add a relationship as a pending proposal. It enters canonical data only "
        "after a human approves the proposal."
    )
    body = f"""
<h1>{_t("Add relationship")}</h1>
<p class="muted">
{intro}
</p>
{warning}
{_errors_block(errors or [])}
<form method="post" action="/relationships/new">
<p>
<label>{_t("Subject")}
  <select name="subject">{subject_options}</select>
</label>
<label>{_t("Predicate")}
  <select name="predicate">
    <option value="">{_t("Choose a predicate")}</option>{predicate_options}
  </select>
</label>
<label>{_t("Object")}
  <select name="object">{object_options}</select>
</label>
</p>
<p>
<label>{_t("Start")}
  <input name="start" value="{_esc(values.get("start", ""))}" placeholder="1987"></label>
<label>{_t("End")}
  <input name="end" value="{_esc(values.get("end", ""))}" placeholder="1995"></label>
<label>{_t("Precision")}
  <select name="precision">
    <option value="">{_t("Unspecified")}</option>{precision_options}
  </select>
</label>
</p>
<p>
<label>{_t("Visibility")}
  <select name="visibility">
    <option value="">{_t("Unspecified")}</option>{visibility_options}
  </select>
</label>
</p>
<label>{_t("Notes")}
  <textarea name="notes" spellcheck="true"
    placeholder="{_t("Optional notes about this relationship")}">{notes_value}</textarea>
</label>
{evidence_block}
<p>
  <button class="primary" type="submit">{_t("Save pending proposal")}</button>
  <a class="button" href="/proposals/new">{_t("Advanced JSON editor")}</a>
  <a class="button" href="/proposals">{_t("Cancel")}</a>
</p>
</form>
"""
    return _layout(_t("Add relationship"), body)


def _targetable_records(root: Path) -> list[tuple[str, str, str]]:
    records, _ = validate_mod.load_records(root)
    items: list[tuple[str, str, str]] = []
    for _, data in records:
        record_id = data.get("id")
        record_type = data.get("type")
        if (
            not isinstance(record_id, str)
            or record_type not in ANNOTATION_TARGET_TYPES
            or data.get("status") in {"archived", "rejected", "superseded"}
        ):
            continue
        items.append((record_id, str(record_type), _record_name(data)))
    return sorted(items, key=lambda item: (item[1], item[2].casefold(), item[0]))


def _assertable_records(root: Path) -> list[tuple[str, str, str]]:
    records, _ = validate_mod.load_records(root)
    items: list[tuple[str, str, str]] = []
    for _, data in records:
        record_id = data.get("id")
        record_type = data.get("type")
        if (
            not isinstance(record_id, str)
            or record_type not in ASSERTION_ENTITY_TYPES
            or data.get("status") in {"archived", "rejected", "superseded"}
        ):
            continue
        items.append((record_id, str(record_type), _record_name(data)))
    return sorted(items, key=lambda item: (item[1], item[2].casefold(), item[0]))


def _assertion_proposal(
    root: Path, values: dict[str, str], evidence: list[str]
) -> tuple[dict[str, Any] | None, list[str]]:
    subject = values.get("subject", "").strip()
    predicate = values.get("predicate", "").strip()
    object_id = values.get("object", "").strip()
    literal = values.get("value", "").strip()
    status = values.get("status", "").strip() or "reported"
    start = values.get("start", "").strip()
    end = values.get("end", "").strip()
    precision = values.get("precision", "").strip()
    visibility = values.get("visibility", "").strip()
    notes = values.get("notes", "").strip()
    evidence = list(dict.fromkeys(item for item in evidence if item))

    known = {record_id for record_id, _, _ in _assertable_records(root)}
    errors: list[str] = []
    if not subject:
        errors.append(_t("Subject is required"))
    elif subject not in known:
        errors.append(_t("Unknown record: {value}", value=subject))
    if not re.fullmatch(r"relation:[A-Za-z0-9][A-Za-z0-9._~-]*", predicate):
        errors.append(_t("Invalid predicate: {value}", value=predicate or "(empty)"))
    if object_id and literal:
        errors.append(_t("Provide either an object record or a literal value, not both"))
    elif not object_id and not literal:
        errors.append(_t("Object or value is required"))
    if object_id and object_id not in known:
        errors.append(_t("Unknown record: {value}", value=object_id))
    if object_id and subject and object_id == subject:
        errors.append(_t("Subject and object must be different"))
    if status not in ASSERTION_STATUSES:
        errors.append(_t("Unsupported status: {value}", value=status))
    if visibility and visibility not in VISIBILITIES:
        errors.append(_t("Unsupported visibility: {value}", value=visibility))
    known_evidence = {record_id for record_id, _, _ in _evidence_records(root)}
    if not evidence:
        errors.append(_t("Evidence is required"))
    for record_id in evidence:
        if record_id not in known_evidence:
            errors.append(_t("Unknown evidence: {value}", value=record_id))
    if errors:
        return None, errors

    now = datetime.now(UTC).isoformat()
    token = uuid4().hex[:12]
    slug = _slug(predicate.removeprefix("relation:")) or "assertion"
    record: dict[str, Any] = {
        "id": f"assertion:{slug}-{token}",
        "type": "Assertion",
        "subject": subject,
        "predicate": predicate,
        "status": status,
        "created_at": now,
        "updated_at": now,
        "transaction_time": {"recorded_at": now},
    }
    if object_id:
        record["object"] = object_id
    else:
        record["value"] = literal
    valid_time: dict[str, str] = {}
    if start:
        valid_time["start"] = start
    if end:
        valid_time["end"] = end
    if precision:
        valid_time["precision"] = precision
    if valid_time:
        record["valid_time"] = valid_time
    produced_by = sorted(item for item in evidence if item.startswith("episode:"))
    supported_by = sorted(item for item in evidence if item.startswith("source:"))
    annotation_refs = sorted(item for item in evidence if item.startswith("annotation:"))
    if produced_by:
        record["produced_by"] = produced_by
    if supported_by:
        record["supported_by"] = supported_by
    if annotation_refs:
        record["annotations"] = annotation_refs
    if visibility:
        record["visibility"] = visibility
    if notes:
        record["notes"] = notes

    record_errors = validate_mod.validate_instance(root, record, TYPE_BY_NAME["Assertion"])
    if record_errors:
        return None, record_errors

    names = {record_id: name for record_id, _, name in _assertable_records(root)}
    proposal = {
        "id": f"proposal:assertion-{token}",
        "type": "Proposal",
        "status": "proposed",
        "created_at": now,
        "updated_at": now,
        "title": _t(
            "New assertion: {subject} {predicate} {object}",
            subject=names.get(subject, subject),
            predicate=predicate,
            object=names.get(object_id, object_id or literal),
        ),
        "rationale": _t("Created from the Add assertion form."),
        "operations": [
            {
                "op": "create",
                "record_type": "Assertion",
                "record": record,
                "evidence": evidence,
            }
        ],
    }
    return proposal, []


def render_assertion_form(
    root: Path,
    values: dict[str, str] | None = None,
    errors: list[str] | None = None,
    selected_evidence: list[str] | None = None,
) -> str:
    values = values or {}
    subject = values.get("subject") or ""
    predicate = values.get("predicate") or ""
    object_id = values.get("object") or ""
    status = values.get("status") or "reported"
    precision = values.get("precision") or ""
    visibility = values.get("visibility") or ""
    notes_value = _esc(values.get("notes", ""))
    records = _assertable_records(root)
    warning = ""
    if not records:
        warning = (
            f'<p class="warning">{_t("Add at least one record before adding an assertion.")}</p>'
        )
    subject_options = f'<option value="">{_t("Choose a record")}</option>' + "".join(
        f'<option value="{_esc(record_id)}"'
        f"{' selected' if record_id == subject else ''}>"
        f"{_esc(record_type)} · {_esc(name or record_id)} · {_esc(record_id)}</option>"
        for record_id, record_type, name in records
    )
    object_options = f'<option value="">{_t("Literal value")}</option>' + "".join(
        f'<option value="{_esc(record_id)}"'
        f"{' selected' if record_id == object_id else ''}>"
        f"{_esc(record_type)} · {_esc(name or record_id)} · {_esc(record_id)}</option>"
        for record_id, record_type, name in records
    )
    predicate_list = "".join(
        f'<option value="{_esc(item)}"></option>' for item in ASSERTION_PREDICATES
    )
    status_options = "".join(
        f'<option value="{_esc(item)}"'
        f"{' selected' if item == status else ''}>{_esc(_t(item))}</option>"
        for item in ASSERTION_STATUSES
    )
    precision_options = "".join(
        f'<option value="{_esc(item)}"'
        f"{' selected' if item == precision else ''}>{_esc(_t(item))}</option>"
        for item in ("day", "month", "year", "decade", "approximate", "unknown")
    )
    visibility_options = "".join(
        f'<option value="{_esc(item)}"'
        f"{' selected' if item == visibility else ''}>{_esc(_t(item))}</option>"
        for item in VISIBILITIES
    )
    evidence_block = _evidence_fieldset(root, selected_evidence)
    intro = _t(
        "Add an assertion as a pending proposal. Choose a subject, a relation "
        "predicate and either an object record or a literal value. It enters "
        "canonical data only after a human approves the proposal."
    )
    body = f"""
<h1>{_t("Add assertion")}</h1>
<p class="muted">
{intro}
</p>
{warning}
{_errors_block(errors or [])}
<form method="post" action="/assertions/new">
<p>
<label>{_t("Subject")}
  <select name="subject">{subject_options}</select>
</label>
<label>{_t("Predicate")}
  <input name="predicate" list="assertion-predicates"
    value="{_esc(predicate)}" placeholder="relation:lived_in">
  <datalist id="assertion-predicates">{predicate_list}</datalist>
</label>
<label>{_t("Object")}
  <select name="object">{object_options}</select>
</label>
<label>{_t("Value")}
  <input name="value" value="{_esc(values.get("value", ""))}"
    placeholder="{_t("Literal value when no object record is chosen")}">
</label>
</p>
<p>
<label>{_t("Status")}
  <select name="status">{status_options}</select>
</label>
<label>{_t("Start")}
  <input name="start" value="{_esc(values.get("start", ""))}" placeholder="1987"></label>
<label>{_t("End")}
  <input name="end" value="{_esc(values.get("end", ""))}" placeholder="1995"></label>
<label>{_t("Precision")}
  <select name="precision">
    <option value="">{_t("Unspecified")}</option>{precision_options}
  </select>
</label>
</p>
<p>
<label>{_t("Visibility")}
  <select name="visibility">
    <option value="">{_t("Unspecified")}</option>{visibility_options}
  </select>
</label>
</p>
<label>{_t("Notes")}
  <textarea name="notes" spellcheck="true"
    placeholder="{_t("Optional notes about this assertion")}">{notes_value}</textarea>
</label>
{evidence_block}
<p>
  <button class="primary" type="submit">{_t("Save pending proposal")}</button>
  <a class="button" href="/proposals/new">{_t("Advanced JSON editor")}</a>
  <a class="button" href="/proposals">{_t("Cancel")}</a>
</p>
</form>
"""
    return _layout(_t("Add assertion"), body)


def _annotation_proposal(
    root: Path, values: dict[str, str], targets: list[str], evidence: list[str]
) -> tuple[dict[str, Any] | None, list[str]]:
    notes = values.get("notes", "").strip()
    visibility = values.get("visibility", "").strip()
    evidence = list(dict.fromkeys(item for item in evidence if item))
    targets = list(dict.fromkeys(item for item in targets if item))

    known_targets = {record_id for record_id, _, _ in _targetable_records(root)}
    known_evidence = {record_id for record_id, _, _ in _evidence_records(root)}
    errors: list[str] = []
    if not targets:
        errors.append(_t("At least one target is required"))
    for record_id in targets:
        if record_id not in known_targets:
            errors.append(_t("Unknown record: {value}", value=record_id))
    if visibility and visibility not in VISIBILITIES:
        errors.append(_t("Unsupported visibility: {value}", value=visibility))
    if not evidence:
        errors.append(_t("Evidence is required"))
    for record_id in evidence:
        if record_id not in known_evidence:
            errors.append(_t("Unknown evidence: {value}", value=record_id))
    if errors:
        return None, errors

    now = datetime.now(UTC).isoformat()
    token = uuid4().hex[:12]
    slug = _slug(" ".join(targets)) or "annotation"
    record: dict[str, Any] = {
        "id": f"annotation:{slug[:24]}-{token}",
        "type": "Annotation",
        "status": "reported",
        "created_at": now,
        "updated_at": now,
        "target_ids": targets,
    }
    episode_ids = sorted(item for item in evidence if item.startswith("episode:"))
    source_ids = sorted(item for item in evidence if item.startswith("source:"))
    if episode_ids:
        record["episode_ids"] = episode_ids
    if source_ids:
        record["source_ids"] = source_ids
    if notes:
        record["notes"] = notes
    if visibility:
        record["visibility"] = visibility

    record_errors = validate_mod.validate_instance(root, record, TYPE_BY_NAME["Annotation"])
    if record_errors:
        return None, record_errors

    proposal = {
        "id": f"proposal:annotation-{token}",
        "type": "Proposal",
        "status": "proposed",
        "created_at": now,
        "updated_at": now,
        "title": _t("New annotation: {count} target(s)", count=len(targets)),
        "rationale": _t("Created from the Add annotation form."),
        "operations": [
            {
                "op": "create",
                "record_type": "Annotation",
                "record": record,
                "evidence": evidence,
            }
        ],
    }
    return proposal, []


def render_annotation_form(
    root: Path,
    values: dict[str, str] | None = None,
    errors: list[str] | None = None,
    selected_targets: list[str] | None = None,
    selected_evidence: list[str] | None = None,
) -> str:
    values = values or {}
    visibility = values.get("visibility") or ""
    notes_value = _esc(values.get("notes", ""))
    targets = _targetable_records(root)
    warning = ""
    if not targets:
        warning = (
            f'<p class="warning">{_t("Add at least one record before adding an annotation.")}</p>'
        )
    selected = set(selected_targets or [])
    target_options = "".join(
        f'<label class="checkbox"><input type="checkbox" name="targets" '
        f'value="{_esc(record_id)}"{" checked" if record_id in selected else ""}> '
        f"{_esc(record_type)} · {_esc(name or record_id)} · {_esc(record_id)}</label>"
        for record_id, record_type, name in targets
    )
    visibility_options = "".join(
        f'<option value="{_esc(item)}"'
        f"{' selected' if item == visibility else ''}>{_esc(_t(item))}</option>"
        for item in VISIBILITIES
    )
    evidence_block = _evidence_fieldset(root, selected_evidence)
    intro = _t(
        "Add an annotation as a pending proposal. Choose the records it annotates "
        "and the evidence behind it. It enters canonical data only after approval."
    )
    body = f"""
<h1>{_t("Add annotation")}</h1>
<p class="muted">{intro}</p>
{warning}
{_errors_block(errors or [])}
<form method="post" action="/annotations/new">
<fieldset><legend>{_t("Targets")}</legend>
{target_options or f'<p class="muted">{_t("None.")}</p>'}
</fieldset>
<p>
<label>{_t("Visibility")}
  <select name="visibility">
    <option value="">{_t("Unspecified")}</option>{visibility_options}
  </select>
</label>
</p>
<label>{_t("Notes")}
  <textarea name="notes" spellcheck="true"
    placeholder="{_t("Optional notes about this annotation")}">{notes_value}</textarea>
</label>
{evidence_block}
<p>
  <button class="primary" type="submit">{_t("Save pending proposal")}</button>
  <a class="button" href="/proposals/new">{_t("Advanced JSON editor")}</a>
  <a class="button" href="/proposals">{_t("Cancel")}</a>
</p>
</form>
"""
    return _layout(_t("Add annotation"), body)


def _narrative_proposal(
    root: Path,
    values: dict[str, str],
    related: list[str],
    evidence: list[str],
) -> tuple[dict[str, Any] | None, list[str]]:
    author = values.get("author", "").strip()
    language = values.get("language", "").strip()
    perspective = values.get("perspective", "").strip()
    content_location = values.get("content_location", "").strip()
    visibility = values.get("visibility", "").strip()
    notes = values.get("notes", "").strip()
    evidence = list(dict.fromkeys(item for item in evidence if item))
    related = list(dict.fromkeys(item for item in related if item))

    known_records = {record_id for record_id, _, _ in _targetable_records(root)}
    known_evidence = {record_id for record_id, _, _ in _evidence_records(root)}
    errors: list[str] = []
    if visibility and visibility not in VISIBILITIES:
        errors.append(_t("Unsupported visibility: {value}", value=visibility))
    for record_id in related:
        if record_id not in known_records:
            errors.append(_t("Unknown record: {value}", value=record_id))
    if not evidence:
        errors.append(_t("Evidence is required"))
    for record_id in evidence:
        if record_id not in known_evidence:
            errors.append(_t("Unknown evidence: {value}", value=record_id))
    if errors:
        return None, errors

    now = datetime.now(UTC).isoformat()
    token = uuid4().hex[:12]
    slug = _slug(author or "narrative") or "narrative"
    record: dict[str, Any] = {
        "id": f"narrative:{slug[:24]}-{token}",
        "type": "Narrative",
        "status": "reported",
        "created_at": now,
        "updated_at": now,
    }
    if author:
        record["author"] = author
    if language:
        record["language"] = language
    if perspective:
        record["perspective"] = perspective
    if content_location:
        record["content_location"] = content_location
    if related:
        record["related_ids"] = related
    source_ids = sorted(item for item in evidence if item.startswith("source:"))
    if source_ids:
        record["source_ids"] = source_ids
    if visibility:
        record["visibility"] = visibility
    if notes:
        record["notes"] = notes

    record_errors = validate_mod.validate_instance(root, record, TYPE_BY_NAME["Narrative"])
    if record_errors:
        return None, record_errors

    proposal = {
        "id": f"proposal:narrative-{token}",
        "type": "Proposal",
        "status": "proposed",
        "created_at": now,
        "updated_at": now,
        "title": _t("New narrative: {author}", author=author or _t("Narrative")),
        "rationale": _t("Created from the Add narrative form."),
        "operations": [
            {
                "op": "create",
                "record_type": "Narrative",
                "record": record,
                "evidence": evidence,
            }
        ],
    }
    return proposal, []


def render_narrative_form(
    root: Path,
    values: dict[str, str] | None = None,
    errors: list[str] | None = None,
    selected_related: list[str] | None = None,
    selected_evidence: list[str] | None = None,
) -> str:
    values = values or {}
    visibility = values.get("visibility") or ""
    notes_value = _esc(values.get("notes", ""))
    records = _targetable_records(root)
    warning = ""
    if not records:
        warning = (
            f'<p class="warning">{_t("Add at least one record before adding a narrative.")}</p>'
        )
    selected = set(selected_related or [])
    related_options = "".join(
        f'<label class="checkbox"><input type="checkbox" name="related" '
        f'value="{_esc(record_id)}"{" checked" if record_id in selected else ""}> '
        f"{_esc(record_type)} · {_esc(name or record_id)} · {_esc(record_id)}</label>"
        for record_id, record_type, name in records
    )
    visibility_options = "".join(
        f'<option value="{_esc(item)}"'
        f"{' selected' if item == visibility else ''}>{_esc(_t(item))}</option>"
        for item in VISIBILITIES
    )
    evidence_block = _evidence_fieldset(root, selected_evidence)
    intro = _t(
        "Add a narrative as a pending proposal. It enters canonical data only "
        "after a human approves the proposal."
    )
    body = f"""
<h1>{_t("Add narrative")}</h1>
<p class="muted">{intro}</p>
{warning}
{_errors_block(errors or [])}
<form method="post" action="/narratives/new">
<p>
<label>{_t("Author")}
  <input name="author" value="{_esc(values.get("author", ""))}"></label>
<label>{_t("Language")}
  <input name="language" value="{_esc(values.get("language", ""))}" placeholder="it"></label>
<label>{_t("Perspective")}
  <input name="perspective" value="{_esc(values.get("perspective", ""))}"></label>
<label>{_t("Content location")}
  <input name="content_location" value="{_esc(values.get("content_location", ""))}"></label>
<label>{_t("Visibility")}
  <select name="visibility">
    <option value="">{_t("Unspecified")}</option>{visibility_options}
  </select>
</label>
</p>
<fieldset><legend>{_t("Related records")}</legend>
{related_options or f'<p class="muted">{_t("None.")}</p>'}
</fieldset>
<label>{_t("Notes")}
  <textarea name="notes" spellcheck="true"
    placeholder="{_t("Optional notes about this narrative")}">{notes_value}</textarea>
</label>
{evidence_block}
<p>
  <button class="primary" type="submit">{_t("Save pending proposal")}</button>
  <a class="button" href="/proposals/new">{_t("Advanced JSON editor")}</a>
  <a class="button" href="/proposals">{_t("Cancel")}</a>
</p>
</form>
"""
    return _layout(_t("Add narrative"), body)


def _conflict_proposal(
    root: Path,
    values: dict[str, str],
    assertions: list[str],
    evidence: list[str],
) -> tuple[dict[str, Any] | None, list[str]]:
    relation = values.get("relation", "").strip()
    reason = values.get("reason", "").strip()
    status = values.get("status", "").strip() or "open"
    visibility = values.get("visibility", "").strip()
    notes = values.get("notes", "").strip()
    assertions = list(dict.fromkeys(item for item in assertions if item))
    evidence = list(dict.fromkeys(item for item in evidence if item))

    known_assertions = {
        record_id
        for record_id, record_type, _ in _targetable_records(root)
        if record_type == "Assertion"
    }
    known_evidence = {record_id for record_id, _, _ in _evidence_records(root)}
    errors: list[str] = []
    if len(assertions) < 2:
        errors.append(_t("At least two assertions are required"))
    for record_id in assertions:
        if record_id not in known_assertions:
            errors.append(_t("Unknown record: {value}", value=record_id))
    if relation and relation not in ("contradicts", "inconsistent", "competing"):
        errors.append(_t("Unsupported relation: {value}", value=relation))
    if status not in ("open", "under_review", "resolved", "accepted_as_plural", "rejected"):
        errors.append(_t("Unsupported status: {value}", value=status))
    if visibility and visibility not in VISIBILITIES:
        errors.append(_t("Unsupported visibility: {value}", value=visibility))
    if not evidence:
        errors.append(_t("Evidence is required"))
    for record_id in evidence:
        if record_id not in known_evidence:
            errors.append(_t("Unknown evidence: {value}", value=record_id))
    if errors:
        return None, errors

    now = datetime.now(UTC).isoformat()
    token = uuid4().hex[:12]
    record: dict[str, Any] = {
        "id": f"conflict:{token}",
        "type": "Conflict",
        "assertions": assertions,
        "status": status,
        "created_at": now,
        "updated_at": now,
    }
    if relation:
        record["relation"] = relation
    if reason:
        record["reason"] = reason
    if visibility:
        record["visibility"] = visibility
    if notes:
        record["notes"] = notes

    record_errors = validate_mod.validate_instance(root, record, TYPE_BY_NAME["Conflict"])
    if record_errors:
        return None, record_errors

    proposal = {
        "id": f"proposal:conflict-{token}",
        "type": "Proposal",
        "status": "proposed",
        "created_at": now,
        "updated_at": now,
        "title": _t("New conflict: {count} assertions", count=len(assertions)),
        "rationale": _t("Created from the Add conflict form."),
        "operations": [
            {
                "op": "create",
                "record_type": "Conflict",
                "record": record,
                "evidence": evidence,
            }
        ],
    }
    return proposal, []


def render_conflict_form(
    root: Path,
    values: dict[str, str] | None = None,
    errors: list[str] | None = None,
    selected_assertions: list[str] | None = None,
    selected_evidence: list[str] | None = None,
) -> str:
    values = values or {}
    relation = values.get("relation") or ""
    status = values.get("status") or "open"
    visibility = values.get("visibility") or ""
    reason_value = _esc(values.get("reason", ""))
    assertions = [item for item in _targetable_records(root) if item[1] == "Assertion"]
    warning = ""
    if len(assertions) < 2:
        warning = (
            f'<p class="warning">{_t("Add at least two assertions before adding a conflict.")}</p>'
        )
    selected = set(selected_assertions or [])
    assertion_options = "".join(
        f'<label class="checkbox"><input type="checkbox" name="assertions" '
        f'value="{_esc(record_id)}"{" checked" if record_id in selected else ""}> '
        f"{_esc(name or record_id)} · {_esc(record_id)}</label>"
        for record_id, _, name in assertions
    )
    relation_options = "".join(
        f'<option value="{_esc(item)}"'
        f"{' selected' if item == relation else ''}>{_esc(item)}</option>"
        for item in ("contradicts", "inconsistent", "competing")
    )
    status_options = "".join(
        f'<option value="{_esc(item)}"'
        f"{' selected' if item == status else ''}>{_esc(_t(item))}</option>"
        for item in ("open", "under_review", "resolved", "accepted_as_plural", "rejected")
    )
    visibility_options = "".join(
        f'<option value="{_esc(item)}"'
        f"{' selected' if item == visibility else ''}>{_esc(_t(item))}</option>"
        for item in VISIBILITIES
    )
    evidence_block = _evidence_fieldset(root, selected_evidence)
    intro = _t(
        "Add an explicit conflict as a pending proposal. It enters canonical data "
        "only after a human approves the proposal."
    )
    body = f"""
<h1>{_t("Add conflict")}</h1>
<p class="muted">{intro}</p>
{warning}
{_errors_block(errors or [])}
<form method="post" action="/conflicts/new">
<fieldset><legend>{_t("Assertions")}</legend>
{assertion_options or f'<p class="muted">{_t("None.")}</p>'}
</fieldset>
<p>
<label>{_t("Relation")}
  <select name="relation">
    <option value="">{_t("Unspecified")}</option>{relation_options}
  </select>
</label>
<label>{_t("Status")}
  <select name="status">{status_options}</select>
</label>
<label>{_t("Visibility")}
  <select name="visibility">
    <option value="">{_t("Unspecified")}</option>{visibility_options}
  </select>
</label>
</p>
<label>{_t("Reason")}
  <input name="reason" value="{reason_value}" style="width:100%"></label>
<label>{_t("Notes")}
  <textarea name="notes" spellcheck="true">{_esc(values.get("notes", ""))}</textarea>
</label>
{evidence_block}
<p>
  <button class="primary" type="submit">{_t("Save pending proposal")}</button>
  <a class="button" href="/proposals/new">{_t("Advanced JSON editor")}</a>
  <a class="button" href="/proposals">{_t("Cancel")}</a>
</p>
</form>
"""
    return _layout(_t("Add conflict"), body)


def _media_asset_proposal(
    root: Path, values: dict[str, str], evidence: list[str]
) -> tuple[dict[str, Any] | None, list[str]]:
    visibility = values.get("visibility", "").strip()
    notes = values.get("notes", "").strip()
    evidence = list(dict.fromkeys(item for item in evidence if item))

    known_evidence = {record_id for record_id, _, _ in _evidence_records(root)}
    errors: list[str] = []
    if visibility and visibility not in VISIBILITIES:
        errors.append(_t("Unsupported visibility: {value}", value=visibility))
    if not evidence:
        errors.append(_t("Evidence is required"))
    for record_id in evidence:
        if record_id not in known_evidence:
            errors.append(_t("Unknown evidence: {value}", value=record_id))
    if errors:
        return None, errors

    now = datetime.now(UTC).isoformat()
    token = uuid4().hex[:12]
    record: dict[str, Any] = {
        "id": f"media:asset-{token}",
        "type": "MediaAsset",
        "status": "reported",
        "created_at": now,
        "updated_at": now,
    }
    if visibility:
        record["visibility"] = visibility
    if notes:
        record["notes"] = notes

    record_errors = validate_mod.validate_instance(root, record, TYPE_BY_NAME["MediaAsset"])
    if record_errors:
        return None, record_errors

    proposal = {
        "id": f"proposal:media-asset-{token}",
        "type": "Proposal",
        "status": "proposed",
        "created_at": now,
        "updated_at": now,
        "title": _t("New media asset"),
        "rationale": _t("Created from the Add media asset form."),
        "operations": [
            {
                "op": "create",
                "record_type": "MediaAsset",
                "record": record,
                "evidence": evidence,
            }
        ],
    }
    return proposal, []


def render_media_asset_form(
    root: Path,
    values: dict[str, str] | None = None,
    errors: list[str] | None = None,
    selected_evidence: list[str] | None = None,
) -> str:
    values = values or {}
    visibility = values.get("visibility") or ""
    notes_value = _esc(values.get("notes", ""))
    visibility_options = "".join(
        f'<option value="{_esc(item)}"'
        f"{' selected' if item == visibility else ''}>{_esc(_t(item))}</option>"
        for item in VISIBILITIES
    )
    evidence_block = _evidence_fieldset(root, selected_evidence)
    intro = _t(
        "Add a media asset as a pending proposal. It enters canonical data only "
        "after a human approves the proposal."
    )
    body = f"""
<h1>{_t("Add media asset")}</h1>
<p class="muted">{intro}</p>
{_errors_block(errors or [])}
<form method="post" action="/media-assets/new">
<p>
<label>{_t("Visibility")}
  <select name="visibility">
    <option value="">{_t("Unspecified")}</option>{visibility_options}
  </select>
</label>
</p>
<label>{_t("Notes")}
  <textarea name="notes" spellcheck="true"
    placeholder="{_t("Optional notes about this media asset")}">{notes_value}</textarea>
</label>
{evidence_block}
<p>
  <button class="primary" type="submit">{_t("Save pending proposal")}</button>
  <a class="button" href="/proposals/new">{_t("Advanced JSON editor")}</a>
  <a class="button" href="/proposals">{_t("Cancel")}</a>
</p>
</form>
"""
    return _layout(_t("Add media asset"), body)


def render_memory_form(
    values: dict[str, str] | None = None, errors: list[str] | None = None
) -> str:
    values = values or {}
    episode_type = values.get("episode_type") or "memory"
    visibility = values.get("visibility") or ""
    type_options = "".join(
        f'<option value="{_esc(item)}"'
        f"{' selected' if item == episode_type else ''}>{_esc(_t(item))}</option>"
        for item in MEMORY_EPISODE_TYPES
    )
    visibility_options = "".join(
        f'<option value="{_esc(item)}"'
        f"{' selected' if item == visibility else ''}>{_esc(_t(item))}</option>"
        for item in VISIBILITIES
    )
    intro = _t(
        "Save a memory as a pending proposal. It does not enter canonical data "
        "until a human approves the proposal; use the advanced JSON editor for "
        "other record types."
    )
    body = f"""
<h1>{_t("Add memory")}</h1>
<p class="muted">
{intro}
</p>
{_errors_block(errors or [])}
<form method="post" action="/memories/new">
<label>{_t("Title")}
  <input name="title" value="{_esc(values.get("title", ""))}" style="width:100%">
</label>
<p>
<label>{_t("Type")} <select name="episode_type">{type_options}</select></label>
<label>{_t("Captured at")}
  <input name="captured_at" value="{_esc(values.get("captured_at", ""))}"
         placeholder="1987 or 1987-05-01"></label>
<label>{_t("Visibility")}
  <select name="visibility">
    <option value="">{_t("Unspecified")}</option>{visibility_options}
  </select>
</label>
</p>
<label>{_t("Memory")}
  <textarea name="text" spellcheck="true"
    placeholder="{_t("Write the memory...")}">{_esc(values.get("text", ""))}</textarea>
</label>
<p>
<label>{_t("Participants")}
  <input name="participants" value="{_esc(values.get("participants", ""))}"
         placeholder="person:anna, person:bruno" style="width:100%"></label>
<label>{_t("Tags")}
  <input name="tags" value="{_esc(values.get("tags", ""))}"
         placeholder="{_t("family, torino")}" style="width:100%"></label>
</p>
<p>
  <button class="primary" type="submit">{_t("Save pending proposal")}</button>
  <a class="button" href="/proposals/new">{_t("Advanced JSON editor")}</a>
  <a class="button" href="/proposals">{_t("Cancel")}</a>
</p>
</form>
"""
    return _layout(_t("Add memory"), body)


def _visibility_filter(query: str) -> set[str] | None:
    values = set(_split_csv(_query_value(query, "visibility")))
    if not values:
        return None
    return values


def render_export(root: Path, query: str) -> tuple[int, str, str, dict[str, str]]:
    export_format = _query_value(query, "format") or "json"
    if export_format not in EXPORT_FORMATS:
        return (
            400,
            _layout(
                _t("Export"),
                f"<h1>{_t('Unsupported export format')}</h1>"
                f"<p>{_esc(export_format)}</p>"
                f'<p><a class="button" href="/records">{_t("Back to records")}</a></p>',
            ),
            "text/html; charset=utf-8",
            {},
        )
    visibility = _visibility_filter(query)
    if visibility is not None:
        invalid = sorted(visibility - set(VISIBILITIES))
        if invalid:
            return (
                400,
                _layout(
                    _t("Export"),
                    f"<h1>{_t('Unsupported visibility')}</h1>"
                    f"<p>{_esc(', '.join(invalid))}</p>"
                    f'<p><a class="button" href="/records">{_t("Back to records")}</a></p>',
                ),
                "text/html; charset=utf-8",
                {},
            )
    try:
        if export_format == "json":
            payload = json.dumps(
                export_mod.export_json(root, visibility), indent=2, ensure_ascii=False
            )
        elif export_format == "jsonld":
            payload = json.dumps(
                export_mod.export_jsonld(root, visibility), indent=2, ensure_ascii=False
            )
        elif export_format == "yaml":
            payload = export_mod.export_yaml(root, visibility)
        else:
            payload = export_mod.export_markdown(root, visibility)
    except export_mod.ExportError as exc:
        return (
            500,
            _layout(
                _t("Export"),
                f"<h1>{_t('Could not export archive')}</h1><p>{_esc(exc)}</p>",
            ),
            "text/html; charset=utf-8",
            {},
        )
    content_type, filename = EXPORT_FORMATS[export_format]
    headers = {"Content-Disposition": f'attachment; filename="{filename}"'}
    return 200, payload, content_type, headers


def render_records(root: Path, query: str = "") -> str:
    record_type = _query_value(query, "type")
    status = _query_value(query, "status")
    needle = _query_value(query, "q")
    visibility = _query_value(query, "visibility")
    records, load_errors = validate_mod.load_records(root)

    filtered = []
    for path, data in records:
        if record_type and data.get("type") != record_type:
            continue
        if status and data.get("status") != status:
            continue
        if visibility and data.get("visibility") != visibility:
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
            id_cell = f'<span class="muted">{_t("(missing id)")}</span>'
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

    table = f'<p class="muted">{_t("No records match these filters.")}</p>'
    if rows:
        table = (
            f"<table><thead><tr><th>{_t('ID')}</th><th>{_t('Type')}</th>"
            f"<th>{_t('Status')}</th><th>{_t('Name / title')}</th>"
            f"<th>{_t('Updated')}</th><th>{_t('File')}</th></tr></thead><tbody>"
            + "".join(rows)
            + "</tbody></table>"
        )

    type_options = "".join(
        f'<option value="{_esc(item.name)}"'
        f"{' selected' if item.name == record_type else ''}>{_esc(item.name)}</option>"
        for item in RECORD_TYPES
    )
    visibility_options = "".join(
        f'<option value="{_esc(item)}"'
        f"{' selected' if item == visibility else ''}>{_esc(_t(item))}</option>"
        for item in VISIBILITIES
    )
    export_params = [
        (key, value)
        for key, value in (
            ("type", record_type),
            ("status", status),
            ("q", needle),
            ("visibility", visibility),
        )
        if value
    ]
    export_links = " ".join(
        f'<a class="button" href="/export?{_esc(urlencode([*export_params, ("format", fmt)]))}">'
        f"{_t('Export {format}', format=EXPORT_LABELS[fmt])}</a>"
        for fmt in EXPORT_FORMATS
    )
    records_intro = _t(
        "Read-only canonical record browser. Showing {shown} of {total} records.",
        shown=len(filtered),
        total=len(records),
    )
    body = f"""
<h1>{_t("Records")}</h1>
<p class="muted">
{records_intro}
</p>
{_warning_block(load_errors)}
<form class="filters" method="get" action="/records">
  <label>{_t("Type")}
    <select name="type"><option value="">{_t("All types")}</option>{type_options}</select>
  </label>
  <label>{_t("Status")}
    <input name="status" value="{_esc(status)}" placeholder="{_t("confirmed")}">
  </label>
  <label>{_t("Visibility")}
    <select name="visibility">
      <option value="">{_t("All visibilities")}</option>{visibility_options}
    </select>
  </label>
  <label>{_t("Search")}
    <input name="q" value="{_esc(needle)}" placeholder="{_t("id, name, notes")}">
  </label>
  <button type="submit">{_t("Filter")}</button>
  <a class="button" href="/records">{_t("Reset")}</a>
</form>
<p>{export_links}</p>
{table}
"""
    return _layout(_t("Records"), body)


def _operation_record_ids(operation: dict[str, Any]) -> list[str]:
    ids: list[str] = []
    for key in ("record_id", "target_id"):
        value = operation.get(key)
        if isinstance(value, str) and value:
            ids.append(value)
    record = operation.get("record")
    if isinstance(record, dict) and isinstance(record.get("id"), str):
        ids.append(record["id"])
    return ids


def _proposals_for_record(root: Path, record_id: str) -> list[tuple[str, str, str]]:
    results: set[tuple[str, str, str]] = set()
    for _, data in proposals_mod.list_proposals(root, include_applied=True):
        operations = data.get("operations")
        if not isinstance(operations, list):
            continue
        touched = any(
            isinstance(operation, dict) and record_id in _operation_record_ids(operation)
            for operation in operations
        )
        if touched:
            results.add(
                (
                    str(data.get("id") or ""),
                    str(data.get("status") or ""),
                    str(data.get("title") or ""),
                )
            )
    return sorted(results)


def render_record_detail(root: Path, record_id: str) -> tuple[int, str]:
    records, load_errors = validate_mod.load_records(root)
    match = next(
        ((path, data) for path, data in records if data.get("id") == record_id),
        None,
    )
    if match is None:
        return 404, _layout(
            _t("Not found"),
            f"<h1>{_t('Record not found')}</h1>"
            f"<p>{_esc(record_id or _t('(empty id)'))}</p>"
            f'<p><a class="button" href="/records">{_t("Back to records")}</a></p>',
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
    assertion_href = f"/assertions/new?subject={quote(record_id, safe='')}"
    body = f"""
<p><a class="button" href="/records">{_t("Back to records")}</a>
<a class="button" href="{assertion_href}">{_t("Add assertion")}</a></p>
<h1>{_esc(name)}</h1>
<p><span class="badge">{_esc(data.get("type") or _t("unknown"))}</span>
{_status_badge(data.get("status"))} {visibility_badge}</p>
<p class="muted">{_esc(record_id)} · {_esc(_relative_label(root, path))}</p>
{_warning_block(load_errors)}
<h2>{_t("References")}</h2>
{_record_links(references, known_ids)}
<h2>{_t("Referenced by")}</h2>
{_record_links(backlinks, known_ids)}
<h2>{_t("Related proposals")}</h2>
{_related_proposals_html(_proposals_for_record(root, record_id))}
<h2>{_t("Record JSON")}</h2>
<pre>{_esc(json.dumps(data, indent=2, ensure_ascii=False))}</pre>
"""
    return 200, _layout(record_id, body)


def render_timeline(root: Path, query: str = "") -> tuple[int, str]:
    record_id = _query_value(query, "id")
    records, load_errors = validate_mod.load_records(root)
    known_ids = _known_ids(records)
    if record_id and record_id not in known_ids:
        return 404, _layout(
            _t("Timeline not found"),
            f"<h1>{_t('Unknown record')}</h1><p>{_esc(record_id)}</p>"
            f'<p><a class="button" href="/timeline">'
            f"{_t('Back to archive timeline')}</a></p>",
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
    table = f'<p class="muted">{_t("No timeline entries for {scope}.", scope=scope)}</p>'
    if rows:
        table = (
            f"<table><thead><tr><th>{_t('Valid time')}</th>"
            f"<th>{_t('Assertion')}</th><th>{_t('Subject')}</th>"
            f"<th>{_t('Predicate')}</th><th>{_t('Object')}</th>"
            f"<th>{_t('Status')}</th><th>{_t('Transaction time')}</th>"
            f"<th>{_t('Evidence')}</th></tr></thead><tbody>" + "".join(rows) + "</tbody></table>"
        )

    body = f"""
<h1>{_t("Timeline")}</h1>
<p class="muted">
{_t("Read-only timeline derived from open assertions. Scope: {scope}.", scope=scope)}
</p>
{_warning_block(load_errors)}
<form class="filters" method="get" action="/timeline">
  <label>{_t("Record ID")}
    <input name="id" value="{_esc(record_id)}"
           placeholder="person:... / place:... / collection:..."></label>
  <button type="submit">{_t("Show timeline")}</button>
  <a class="button" href="/timeline">{_t("Archive timeline")}</a>
</form>
{table}
"""
    return 200, _layout(_t("Timeline"), body)


def render_genogram(root: Path, query: str = "") -> tuple[int, str]:
    person_id = _query_value(query, "id")
    at_value = _query_value(query, "at")
    records, load_errors = validate_mod.load_records(root)
    known_ids = _known_ids(records)
    form = f"""
<form class="filters" method="get" action="/genogram">
  <label>{_t("Person ID")}
    <input name="id" value="{_esc(person_id)}" placeholder="person:..."></label>
  <label>{_t("At (year)")}
    <input name="at" value="{_esc(at_value)}" placeholder="1990"></label>
  <button type="submit">{_t("Show genogram")}</button>
</form>
"""
    if not person_id:
        return 400, _layout(
            _t("Genogram"),
            f"<h1>{_t('Genogram')}</h1>"
            f'<p class="muted">{_t("Experimental relationship view. Provide a person ID.")}</p>'
            f"{_errors_block([_t('Provide a person ID')])}{form}",
        )
    if person_id not in known_ids:
        return 404, _layout(
            _t("Genogram not found"),
            f"<h1>{_t('Unknown record')}</h1><p>{_esc(person_id)}</p>"
            f'<p><a class="button" href="/genogram">{_t("Back to genogram")}</a></p>',
        )

    result = build_genogram(root, person_id, at=at_value or None)
    rows = []
    for relation in result["relations"]:
        supported = relation.get("supported")
        supported_badge = (
            f'<span class="badge">{_t("supported")}</span>'
            if supported
            else f'<span class="badge">{_t("unsupported")}</span>'
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

    table = f'<p class="muted">{_t("No relations for {person}.", person=person_id)}</p>'
    if rows:
        table = (
            f"<table><thead><tr><th>{_t('Predicate')}</th>"
            f"<th>{_t('Direction')}</th><th>{_t('Subject')}</th>"
            f"<th>{_t('Object')}</th><th>{_t('Supported')}</th>"
            f"<th>{_t('Source record')}</th>"
            f"<th>{_t('Valid time / valid_times')}</th>"
            f"<th>{_t('Transaction time / transaction_times')}</th>"
            f"<th>{_t('Related records')}</th>"
            "</tr></thead><tbody>" + "".join(rows) + "</tbody></table>"
        )

    body = f"""
<h1>{_t("Genogram: {person}", person=person_id)}</h1>
<div class="warning">
<strong>{_t("Experimental")}</strong>
<p>{
        _t(
            "This relationship view is experimental and has no temporal filter yet. "
            "It derives only from canonical records and never writes data."
        )
    }</p>
</div>
<p class="muted">
{_t("Read-only, derived from relation:* assertions and endpoint-aware Relationship records.")}
</p>
{_warning_block(load_errors)}
{_notice_block(_t("Genogram warnings"), result["warnings"])}
{form}
{table}
"""
    return 200, _layout(_t("Genogram {person}", person=person_id), body)


def _conflict_assertion_rows(
    conflict: dict[str, Any],
    known_ids: set[str],
    canonical: dict[str, dict[str, Any]],
) -> str:
    assertions = [str(item) for item in conflict.get("assertions") or []]
    summaries: dict[str, dict[str, Any]] = dict(canonical)
    for record in conflict.get("assertion_records") or []:
        if isinstance(record, dict) and isinstance(record.get("id"), str):
            summaries[record["id"]] = record
    rows = []
    for assertion_id in assertions:
        record = summaries.get(assertion_id)
        summary = ""
        if record is not None:
            target = record.get("object") or record.get("value") or ""
            summary = (
                f" · {_esc(record.get('subject', ''))} {_esc(record.get('predicate', ''))}"
                f" {_esc(target)}"
            )
        rows.append(
            f'<li>{_record_link(assertion_id, known_ids)}<span class="muted">{summary}</span></li>'
        )
    return f"<ul>{''.join(rows)}</ul>" if rows else f'<p class="muted">{_t("None.")}</p>'


def render_conflicts(root: Path, query: str = "") -> tuple[int, str]:
    status = _query_value(query, "status") or ""
    conflicts = list_conflicts(root, status or None)
    records, load_errors = validate_mod.load_records(root)
    known_ids = _known_ids(records)
    canonical = {
        str(data.get("id")): data for _, data in records if isinstance(data.get("id"), str)
    }

    status_options = "".join(
        f'<option value="{_esc(item)}"'
        f"{' selected' if item == status else ''}>{_esc(_t(item))}</option>"
        for item in CONFLICT_STATUSES
    )
    filter_form = f"""
<form method="get" action="/conflicts" class="filters">
<label>{_t("Status")}
  <select name="status">
    <option value="">{_t("All")}</option>{status_options}
  </select>
</label>
<button type="submit">{_t("Filter")}</button>
<a class="button" href="/conflicts">{_t("Reset")}</a>
</form>
"""
    sections = []
    for conflict in conflicts:
        conflict_id = str(conflict.get("id") or "")
        derived = bool(conflict.get("derived"))
        badges = _status_badge(conflict.get("status"))
        if derived:
            badges += f' <span class="badge">{_t("derived")}</span>'
        relation = conflict.get("relation")
        reason = conflict.get("reason") or conflict.get("notes")
        meta = []
        if relation:
            meta.append(f"{_t('Relation')}: {_esc(relation)}")
        if conflict.get("identified_at"):
            meta.append(f"{_t('Identified')}: {_esc(conflict.get('identified_at'))}")
        meta_html = f'<p class="muted">{" · ".join(meta)}</p>' if meta else ""
        evidence_set = {str(item) for item in conflict.get("evidence") or []}
        if not evidence_set:
            for assertion_id in conflict.get("assertions") or []:
                record = canonical.get(str(assertion_id))
                if record is None:
                    continue
                for field in ("produced_by", "supported_by"):
                    evidence_set.update(str(item) for item in record.get(field) or [])
        evidence = sorted(evidence_set)
        evidence_html = (
            _record_links(evidence, known_ids)
            if evidence
            else f'<p class="muted">{_t("None.")}</p>'
        )
        reason_html = f"<p>{_t('Reason')}: {_esc(reason)}</p>" if reason else ""
        sections.append(
            f"""
<article>
<h2>{_esc(conflict_id)} {badges}</h2>
{meta_html}
<p>{_t("Assertions")}</p>
{_conflict_assertion_rows(conflict, known_ids, canonical)}
<p>{_t("Evidence")}</p>
{evidence_html}
{reason_html}
</article>
"""
        )
    if not sections:
        sections.append(f'<p class="muted">{_t("No conflicts found.")}</p>')

    body = f"""
<h1>{_t("Conflicts")}</h1>
<p class="muted">{
        _t(
            "Explicit conflict records and contradictions derived from assertion links. "
            "This view is read-only."
        )
    }</p>
{_warning_block(load_errors)}
{filter_form}
{"".join(sections)}
"""
    return 200, _layout(_t("Conflicts"), body)


def render_media(root: Path) -> str:
    entries = list_media(root)
    rows = []
    for entry in entries:
        checksum = entry.get("checksum") or {}
        rows.append(
            "<tr>"
            f"<td>{_esc(entry.get('id', ''))}</td>"
            f"<td>{_esc(entry.get('filename', ''))}</td>"
            f"<td>{_esc(entry.get('mime_type') or '—')}</td>"
            f"<td>{_esc(entry.get('size', 0))}</td>"
            f"<td>{_esc((checksum.get('value') or '')[:12])}</td>"
            f"<td>{_esc(entry.get('visibility') or '—')}</td>"
            f"<td>{_esc(entry.get('uri', ''))}</td>"
            "</tr>"
        )
    table = (
        "<table><thead><tr>"
        f"<th>{_t('ID')}</th><th>{_t('File')}</th><th>{_t('MIME')}</th>"
        f"<th>{_t('Size')}</th><th>{_t('SHA-256')}</th>"
        f"<th>{_t('Visibility')}</th><th>{_t('URI')}</th>"
        "</tr></thead><tbody>" + "".join(rows) + "</tbody></table>"
        if rows
        else f'<p class="muted">{_t("No media registered.")}</p>'
    )
    body = f"""
<h1>{_t("Media")}</h1>
<p class="muted">
{_t("Checksummed manifests for media files kept outside Git.")}
</p>
<p><a class="button" href="/records">{_t("Back to records")}</a></p>
{table}
"""
    return _layout(_t("Media"), body)


def render_list(root: Path) -> str:
    body = (
        f"<h1>{_t('Proposals')}</h1>"
        f'<p><a class="button primary" href="/memories/new">{_t("Add memory")}</a> '
        f'<a class="button" href="/proposals/new">{_t("New proposal")}</a> '
        f'<a class="button" href="/proposals/generate">{_t("Generate with Ollama")}</a></p>'
        f"{_proposal_rows(root)}"
    )
    return _layout(_t("Proposals"), body)


def _new_form(value: str = "", errors: list[str] | None = None) -> str:
    body = f"""
<h1>{_t("New proposal")}</h1>
<p class="muted">
{_t("Paste a proposal JSON object. It is saved as pending only; approval is a separate action.")}
</p>
{_errors_block(errors or [])}
<form method="post" action="/proposals/new">
<textarea name="json" spellcheck="false">{_esc(value)}</textarea>
<p>
  <button class="primary" type="submit">{_t("Save pending proposal")}</button>
  <a class="button" href="/proposals">{_t("Cancel")}</a>
</p>
</form>
"""
    return _layout(_t("New proposal"), body)


def _edit_form(proposal_id: str, value: str = "", errors: list[str] | None = None) -> str:
    body = f"""
<h1>{_t("Edit proposal")}</h1>
<p class="muted">
{
        _t(
            "Editing {id}. The proposal ID cannot change; saving replaces the pending JSON.",
            id=proposal_id,
        )
    }
</p>
{_errors_block(errors or [])}
<form method="post" action="/proposals/{quote(proposal_id, safe="")}/edit">
<textarea name="json" spellcheck="false">{_esc(value)}</textarea>
<p>
  <button class="primary" type="submit">{_t("Save pending proposal")}</button>
  <a class="button" href="/proposals/{quote(proposal_id, safe="")}">{_t("Cancel")}</a>
</p>
</form>
"""
    return _layout(_t("Edit {id}", id=proposal_id), body)


def render_generate_form(
    source: str = "",
    errors: list[str] | None = None,
    model: str | None = None,
    base_url: str | None = None,
    provider: str | None = None,
    api_key: str | None = None,
) -> str:
    try:
        config = provider_config(provider, model, base_url, api_key)
    except LLMAdapterError:
        config = ProviderConfig(provider=provider or "ollama")
    intro = _t(
        "A local model turns source text into a pending proposal. It cannot approve "
        "or write canonical data; review the dry-run first. Set "
        "STORYGRAM_LLM_API_KEY in the server environment for providers that require a key."
    )
    body = f"""
<h1>{_t("Generate proposal")}</h1>
<p class="muted">
{intro}
</p>
{_errors_block(errors or [])}
<form method="post" action="/proposals/generate">
<textarea name="source" spellcheck="false"
 placeholder="{_t("Paste an interview, note or memory...")}">{_esc(source)}</textarea>
<p>
<label>{_t("Provider")}
<input name="provider" value="{_esc(config.provider)}" style="padding:6px"></label>
<label>{_t("Model")}
<input name="model" value="{_esc(config.model)}" style="padding:6px"></label>
<label>{_t("LLM URL")}
<input name="url" value="{_esc(config.base_url)}" style="padding:6px; width:20rem"></label>
<label>{_t("API key (optional)")}
<input name="api_key" type="password" value="{_esc(api_key or config.api_key or '')}" style="padding:6px; width:20rem"></label>
</p>
<p>
  <button class="primary" type="submit">{_t("Generate pending proposal")}</button>
  <a class="button" href="/proposals">{_t("Cancel")}</a>
</p>
</form>
"""
    return _layout(_t("Generate proposal"), body)


def _status_is_open(status: Any) -> bool:
    return status in {"draft", "proposed", "under_review", "approved"}


def _affected_records_html(root: Path, proposal: dict[str, Any]) -> str:
    records, _ = validate_mod.load_records(root)
    known_ids = {str(item.get("id")) for _, item in records if isinstance(item.get("id"), str)}
    affected: list[str] = []
    operations = proposal.get("operations")
    for operation in operations if isinstance(operations, list) else []:
        if not isinstance(operation, dict):
            continue
        for record_id in _operation_record_ids(operation):
            if record_id not in affected:
                affected.append(record_id)
    if not affected:
        return f'<p class="muted">{_t("None.")}</p>'
    rows = []
    for record_id in affected:
        if record_id in known_ids:
            rows.append(f'<li><a href="{_esc(_record_href(record_id))}">{_esc(record_id)}</a></li>')
        else:
            rows.append(f'<li>{_esc(record_id)} <span class="muted">{_t("(pending)")}</span></li>')
    return f"<ul>{''.join(rows)}</ul>"


def render_detail(root: Path, proposal_id: str, errors: list[str] | None = None) -> tuple[int, str]:
    path = proposals_mod.find_proposal(root, proposal_id, include_applied=True)
    if path is None:
        return 404, _layout(
            _t("Not found"), f"<h1>{_t('Not found')}</h1><p>{_esc(proposal_id)}</p>"
        )
    data = proposals_mod._load_json(path)
    if data is None:
        return 500, _layout(
            _t("Invalid proposal"),
            f"<h1>{_t('Invalid proposal')}</h1><p>{_esc(proposal_id)}</p>",
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
<h2>{_t("Dry-run preview")}</h2>
<ul>{operations}</ul>
<p class="muted">{_t("Files")}</p><ul>{files}</ul>
<form method="post" action="/proposals/{quote(proposal_id, safe="")}/approve">
<button class="primary" name="commit" value="yes" type="submit">{_t("Approve and commit")}</button>
<button name="commit" value="no" type="submit">{_t("Approve without commit")}</button>
</form>
<form method="post" action="/proposals/{quote(proposal_id, safe="")}/reject">
<p>
<input name="reason" placeholder="{_t("Rejection reason (optional)")}"
       style="width:70%; padding:6px">
</p>
<button type="submit">{_t("Reject")}</button>
</form>
<form method="post" action="/proposals/{quote(proposal_id, safe="")}/withdraw">
<p>
<input name="reason" placeholder="{_t("Withdrawal reason (optional)")}"
       style="width:70%; padding:6px">
</p>
<button type="submit">{_t("Withdraw")}</button>
</form>
"""
        except proposals_mod.ProposalError as exc:
            plan_html = f"<h2>{_t('Dry-run preview')}</h2>{_errors_block(exc.errors)}"

    edit_link = ""
    if path.parent == proposals_mod.pending_dir(root) and _status_is_open(data.get("status")):
        edit_link = (
            f'<a class="button" href="/proposals/{quote(proposal_id, safe="")}/edit">'
            f"{_t('Edit pending proposal')}</a> "
        )

    body = f"""
<h1>{_esc(data.get("id"))}</h1>
<p>
{_status_badge(data.get("status"))}
<span class="muted">{_esc(data.get("title") or "")}</span>
</p>
{_errors_block(errors or [])}
{plan_html}
<h2>{_t("Affected records")}</h2>
{_affected_records_html(root, data)}
<h2>{_t("Proposal JSON")}</h2>
<pre>{_esc(json.dumps(data, indent=2))}</pre>
<p>{edit_link}<a class="button" href="/proposals">{_t("Back")}</a></p>
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

    def _cookie_language(self) -> str | None:
        raw = self.headers.get("Cookie", "")
        for part in raw.split(";"):
            name, _, value = part.strip().partition("=")
            if name == "storygram_lang":
                return normalize_language(value)
        return None

    def _prepare_context(self, parsed: Any) -> None:
        query_language = _query_value(parsed.query, "lang")
        set_language(query_language or self._cookie_language())
        path = parsed.path + (f"?{parsed.query}" if parsed.query else "")
        set_path(path)

    def _send(
        self,
        status: int,
        body: str,
        content_type: str = "text/html; charset=utf-8",
        headers: dict[str, str] | None = None,
    ) -> None:
        encoded = body.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(encoded)))
        self.send_header("Cache-Control", "no-store")
        for name, value in (headers or {}).items():
            self.send_header(name, value)
        self.end_headers()
        self.wfile.write(encoded)

    def _redirect(self, location: str, headers: dict[str, str] | None = None) -> None:
        self.send_response(303)
        self.send_header("Location", location)
        for name, value in (headers or {}).items():
            self.send_header(name, value)
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

    def _api_review(self, proposal_id: str) -> None:
        path = proposals_mod.find_proposal(self.root, proposal_id)
        applied_path = None
        if path is None:
            applied_path = proposals_mod.find_applied_proposal(self.root, proposal_id)
        source_path = path or applied_path
        if source_path is None:
            self._api_error(404, f"proposal not found: {proposal_id}")
            return
        data = proposals_mod._load_json(source_path)
        if not isinstance(data, dict):
            self._api_error(500, f"cannot read proposal: {proposal_id}")
            return
        try:
            body = self._read_json(required=False)
        except APIRequestError as exc:
            self._api_error(exc.status, exc.message)
            return
        provider_name = body.get("provider")
        model = body.get("model")
        base_url = body.get("url", body.get("ollama_url"))
        api_key = body.get("api_key")
        for value, name in (
            (provider_name, "provider"),
            (model, "model"),
            (base_url, "url"),
            (api_key, "api_key"),
        ):
            if value is not None and not isinstance(value, str):
                self._api_error(400, f"{name} must be a string")
                return
        try:
            config = provider_config(provider_name, model, base_url, api_key)
        except LLMAdapterError as exc:
            self._api_error(400, str(exc))
            return
        factory = cast(StorygramServer, self.server).provider_factory
        provider = factory(config) if factory is not None else provider_from_config(config)
        try:
            feedback = review_proposal(provider, data)
        except LLMAdapterError as exc:
            self._api_error(502, str(exc))
            return
        self._send_json(200, {"ok": True, "proposal_id": proposal_id, "review": feedback})

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
            if action in {"reject", "withdraw"}:
                if method != "POST":
                    self._api_error(405, "method not allowed", {"Allow": "POST"})
                    return
                self._api_close(proposal_id, "rejected" if action == "reject" else "withdrawn")
                return
            if action == "review":
                if method != "POST":
                    self._api_error(405, "method not allowed", {"Allow": "POST"})
                    return
                self._api_review(proposal_id)
                return
            self._api_error(404, "API route not found")
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
        self._prepare_context(parsed)
        if path.startswith("/api/"):
            self._handle_api("GET", path, parsed.query)
            return
        if path.startswith("/lang/"):
            language = normalize_language(path.removeprefix("/lang/"))
            next_path = _query_value(parsed.query, "next") or "/"
            if not next_path.startswith("/") or next_path.startswith("//"):
                next_path = "/"
            parts = urlsplit(next_path)
            next_query = parse_qs(parts.query, keep_blank_values=True)
            next_query.pop("lang", None)
            next_path = urlunsplit(
                ("", "", parts.path, urlencode(next_query, doseq=True), parts.fragment)
            )
            cookie = f"storygram_lang={language}; Path=/; SameSite=Lax; Max-Age=31536000"
            self._redirect(next_path, {"Set-Cookie": cookie})
            return
        if path == "/":
            self._send(200, render_home(self.root))
            return
        if path == "/records":
            self._send(200, render_records(self.root, parsed.query))
            return
        if path == "/export":
            status, body, content_type, headers = render_export(self.root, parsed.query)
            self._send(status, body, content_type, headers)
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
        if path == "/conflicts":
            status_code, body = render_conflicts(self.root, parsed.query)
            self._send(status_code, body)
            return
        if path == "/media":
            self._send(200, render_media(self.root))
            return
        if path == "/proposals":
            self._send(200, render_list(self.root))
            return
        if path == "/memories/new":
            self._send(200, render_memory_form())
            return
        if path == "/sources/new":
            self._send(200, render_source_form())
            return
        if path == "/people/new":
            self._send(200, render_person_form(self.root))
            return
        if path == "/entities/new":
            self._send(200, render_entity_form(self.root))
            return
        if path == "/relationships/new":
            self._send(200, render_relationship_form(self.root))
            return
        if path == "/assertions/new":
            prefill = {
                key: _query_value(parsed.query, key)
                for key in ("subject", "object")
                if _query_value(parsed.query, key)
            }
            self._send(200, render_assertion_form(self.root, prefill))
            return
        if path == "/annotations/new":
            self._send(200, render_annotation_form(self.root))
            return
        if path == "/conflicts/new":
            self._send(200, render_conflict_form(self.root))
            return
        if path == "/narratives/new":
            self._send(200, render_narrative_form(self.root))
            return
        if path in {"/media/new", "/media-assets/new", "/mediaassets/new"}:
            self._send(200, render_media_asset_form(self.root))
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
                            _t("Cannot edit"),
                            f"<h1>{_t('Cannot edit applied proposal')}</h1>"
                            f"<p>{_esc(proposal_id)}</p>",
                        ),
                    )
                else:
                    self._send(
                        404,
                        _layout(
                            _t("Not found"),
                            f"<h1>{_t('Not found')}</h1><p>{_esc(proposal_id)}</p>",
                        ),
                    )
                return
            data = proposals_mod._load_json(pending)
            if data is None or not _status_is_open(data.get("status")):
                self._send(
                    409,
                    _layout(
                        _t("Cannot edit"),
                        f"<h1>{_t('Proposal is not editable')}</h1><p>{_esc(proposal_id)}</p>",
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
        self._send(404, _layout(_t("Not found"), f"<h1>{_t('Not found')}</h1>"))

    def do_POST(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        path = unquote(parsed.path)
        self._prepare_context(parsed)
        if path.startswith("/api/"):
            self._handle_api("POST", path, parsed.query)
            return
        try:
            form = self._read_form()
        except ValueError as exc:
            self._send(413, _layout(_t("Bad request"), _errors_block([_t(str(exc))])))
            return

        if path == "/memories/new":
            values = {
                key: (form.get(key) or [""])[0]
                for key in (
                    "title",
                    "episode_type",
                    "captured_at",
                    "text",
                    "participants",
                    "tags",
                    "visibility",
                )
            }
            proposal, errors = _memory_proposal(self.root, values)
            if proposal is None:
                self._send(400, render_memory_form(values, errors))
                return
            try:
                proposals_mod.create_pending(self.root, proposal)
            except proposals_mod.ProposalError as exc:
                self._send(400, render_memory_form(values, exc.errors))
                return
            proposal_id = str(proposal["id"])
            self._redirect(f"/proposals/{quote(proposal_id, safe='')}")
            return

        if path == "/sources/new":
            values = {
                key: (form.get(key) or [""])[0]
                for key in (
                    "title",
                    "source_type",
                    "visibility",
                    "notes",
                )
            }
            proposal, errors = _source_proposal(self.root, values)
            if proposal is None:
                self._send(400, render_source_form(values, errors))
                return
            try:
                proposals_mod.create_pending(self.root, proposal)
            except proposals_mod.ProposalError as exc:
                self._send(400, render_source_form(values, exc.errors))
                return
            proposal_id = str(proposal["id"])
            self._redirect(f"/proposals/{quote(proposal_id, safe='')}")
            return

        if path == "/people/new":
            values = {
                key: (form.get(key) or [""])[0]
                for key in (
                    "name",
                    "notes",
                    "visibility",
                )
            }
            evidence = form.get("evidence") or []
            proposal, errors = _person_proposal(self.root, values, evidence)
            if proposal is None:
                self._send(400, render_person_form(self.root, values, errors, evidence))
                return
            try:
                proposals_mod.create_pending(self.root, proposal)
            except proposals_mod.ProposalError as exc:
                self._send(400, render_person_form(self.root, values, exc.errors, evidence))
                return
            proposal_id = str(proposal["id"])
            self._redirect(f"/proposals/{quote(proposal_id, safe='')}")
            return

        if path == "/entities/new":
            values = {
                key: (form.get(key) or [""])[0]
                for key in (
                    "entity_type",
                    "name",
                    "notes",
                    "visibility",
                )
            }
            evidence = form.get("evidence") or []
            proposal, errors = _entity_proposal(self.root, values, evidence)
            if proposal is None:
                self._send(400, render_entity_form(self.root, values, errors, evidence))
                return
            try:
                proposals_mod.create_pending(self.root, proposal)
            except proposals_mod.ProposalError as exc:
                self._send(400, render_entity_form(self.root, values, exc.errors, evidence))
                return
            proposal_id = str(proposal["id"])
            self._redirect(f"/proposals/{quote(proposal_id, safe='')}")
            return

        if path == "/relationships/new":
            values = {
                key: (form.get(key) or [""])[0]
                for key in (
                    "subject",
                    "predicate",
                    "object",
                    "start",
                    "end",
                    "precision",
                    "visibility",
                    "notes",
                )
            }
            evidence = form.get("evidence") or []
            proposal, errors = _relationship_proposal(self.root, values, evidence)
            if proposal is None:
                self._send(400, render_relationship_form(self.root, values, errors, evidence))
                return
            try:
                proposals_mod.create_pending(self.root, proposal)
            except proposals_mod.ProposalError as exc:
                self._send(400, render_relationship_form(self.root, values, exc.errors, evidence))
                return
            proposal_id = str(proposal["id"])
            self._redirect(f"/proposals/{quote(proposal_id, safe='')}")
            return

        if path == "/assertions/new":
            values = {
                key: (form.get(key) or [""])[0]
                for key in (
                    "subject",
                    "predicate",
                    "object",
                    "value",
                    "status",
                    "start",
                    "end",
                    "precision",
                    "visibility",
                    "notes",
                )
            }
            evidence = form.get("evidence") or []
            proposal, errors = _assertion_proposal(self.root, values, evidence)
            if proposal is None:
                self._send(400, render_assertion_form(self.root, values, errors, evidence))
                return
            try:
                proposals_mod.create_pending(self.root, proposal)
            except proposals_mod.ProposalError as exc:
                self._send(400, render_assertion_form(self.root, values, exc.errors, evidence))
                return
            proposal_id = str(proposal["id"])
            self._redirect(f"/proposals/{quote(proposal_id, safe='')}")
            return

        if path == "/annotations/new":
            values = {
                "notes": (form.get("notes") or [""])[0],
                "visibility": (form.get("visibility") or [""])[0],
            }
            targets = form.get("targets") or []
            evidence = form.get("evidence") or []
            proposal, errors = _annotation_proposal(self.root, values, targets, evidence)
            if proposal is None:
                self._send(
                    400, render_annotation_form(self.root, values, errors, targets, evidence)
                )
                return
            try:
                proposals_mod.create_pending(self.root, proposal)
            except proposals_mod.ProposalError as exc:
                self._send(
                    400, render_annotation_form(self.root, values, exc.errors, targets, evidence)
                )
                return
            proposal_id = str(proposal["id"])
            self._redirect(f"/proposals/{quote(proposal_id, safe='')}")
            return

        if path == "/narratives/new":
            values = {
                key: (form.get(key) or [""])[0]
                for key in (
                    "author",
                    "language",
                    "perspective",
                    "content_location",
                    "visibility",
                    "notes",
                )
            }
            related = form.get("related") or []
            evidence = form.get("evidence") or []
            proposal, errors = _narrative_proposal(self.root, values, related, evidence)
            if proposal is None:
                self._send(400, render_narrative_form(self.root, values, errors, related, evidence))
                return
            try:
                proposals_mod.create_pending(self.root, proposal)
            except proposals_mod.ProposalError as exc:
                self._send(
                    400, render_narrative_form(self.root, values, exc.errors, related, evidence)
                )
                return
            proposal_id = str(proposal["id"])
            self._redirect(f"/proposals/{quote(proposal_id, safe='')}")
            return

        if path == "/conflicts/new":
            values = {
                key: (form.get(key) or [""])[0]
                for key in ("relation", "reason", "status", "visibility", "notes")
            }
            assertions = form.get("assertions") or []
            evidence = form.get("evidence") or []
            proposal, errors = _conflict_proposal(self.root, values, assertions, evidence)
            if proposal is None:
                self._send(
                    400, render_conflict_form(self.root, values, errors, assertions, evidence)
                )
                return
            try:
                proposals_mod.create_pending(self.root, proposal)
            except proposals_mod.ProposalError as exc:
                self._send(
                    400, render_conflict_form(self.root, values, exc.errors, assertions, evidence)
                )
                return
            proposal_id = str(proposal["id"])
            self._redirect(f"/proposals/{quote(proposal_id, safe='')}")
            return

        if path in {"/media/new", "/media-assets/new", "/mediaassets/new"}:
            values = {
                "visibility": (form.get("visibility") or [""])[0],
                "notes": (form.get("notes") or [""])[0],
            }
            evidence = form.get("evidence") or []
            proposal, errors = _media_asset_proposal(self.root, values, evidence)
            if proposal is None:
                self._send(400, render_media_asset_form(self.root, values, errors, evidence))
                return
            try:
                proposals_mod.create_pending(self.root, proposal)
            except proposals_mod.ProposalError as exc:
                self._send(400, render_media_asset_form(self.root, values, exc.errors, evidence))
                return
            proposal_id = str(proposal["id"])
            self._redirect(f"/proposals/{quote(proposal_id, safe='')}")
            return

        if path == "/proposals/generate":
            source = (form.get("source") or [""])[0]
            provider_name = (form.get("provider") or [""])[0].strip() or None
            model = (form.get("model") or [""])[0].strip() or None
            base_url = (form.get("url") or [""])[0].strip() or None
            base_url = base_url or (form.get("ollama_url") or [""])[0].strip() or None
            api_key = (form.get("api_key") or [""])[0].strip() or None
            if not source.strip():
                self._send(
                    400,
                    render_generate_form(
                        source, [_t("Source text is empty")], model, base_url, provider_name, api_key
                    ),
                )
                return
            try:
                config = provider_config(provider_name, model, base_url, api_key)
            except LLMAdapterError as exc:
                self._send(
                    400,
                    render_generate_form(source, [str(exc)], model, base_url, provider_name, api_key),
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
                        source, [str(exc)], config.model, config.base_url, config.provider, api_key
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
                self._send(
                    400,
                    _edit_form(edit_id, raw, [_t("Invalid JSON: {error}", error=exc)]),
                )
                return
            if not isinstance(data, dict):
                self._send(
                    400,
                    _edit_form(edit_id, raw, [_t("Proposal must be a JSON object")]),
                )
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
                self._send(400, _new_form(raw, [_t("Invalid JSON: {error}", error=exc)]))
                return
            if not isinstance(data, dict):
                self._send(400, _new_form(raw, [_t("Proposal must be a JSON object")]))
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

        self._send(404, _layout(_t("Not found"), f"<h1>{_t('Not found')}</h1>"))

    def do_PUT(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        path = unquote(parsed.path)
        self._prepare_context(parsed)
        if path.startswith("/api/"):
            self._handle_api("PUT", path, parsed.query)
            return
        self._send(
            405,
            _layout(_t("Method not allowed"), f"<h1>{_t('Method not allowed')}</h1>"),
        )


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
