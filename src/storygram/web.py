"""Minimal local web UI for proposal review."""

from __future__ import annotations

import html
import json
import os
from collections.abc import Callable
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, cast
from urllib.parse import parse_qs, quote, unquote, urlparse

from . import proposals as proposals_mod
from . import validate as validate_mod
from .llm import LLMAdapter, LLMAdapterError, OllamaProvider, Provider, save_pending
from .registry import RECORD_TYPES, TYPE_BY_NAME

MAX_BODY = 4 * 1024 * 1024


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
</style>
</head>
<body>
<header>
  <strong>Storygram</strong>
  <nav>
    <a href="/">Home</a><a href="/proposals">Proposals</a>
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
  <a class="button primary" href="/proposals/new">Create proposal</a>
  <a class="button" href="/proposals/generate">Generate with Ollama</a>
  <a class="button" href="/proposals">View proposals</a>
</p>
<h2>Record counts</h2><ul>{"".join(counts)}</ul>
"""
    return _layout("Home", body)


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


def render_generate_form(
    source: str = "",
    errors: list[str] | None = None,
    model: str | None = None,
    ollama_url: str | None = None,
) -> str:
    model_value = model or os.environ.get("STORYGRAM_OLLAMA_MODEL", "llama3.2")
    url_value = ollama_url or os.environ.get("STORYGRAM_OLLAMA_URL", "http://127.0.0.1:11434")
    body = f"""
<h1>Generate proposal</h1>
<p class="muted">
A local Ollama model turns source text into a pending proposal. It cannot approve or
write canonical data; review the dry-run first.
</p>
{_errors_block(errors or [])}
<form method="post" action="/proposals/generate">
<textarea name="source" spellcheck="false"
 placeholder="Paste an interview, note or memory...">{_esc(source)}</textarea>
<p><label>Model <input name="model" value="{_esc(model_value)}" style="padding:6px"></label>
<label>Ollama URL
<input name="ollama_url" value="{_esc(url_value)}" style="padding:6px; width:20rem"></label></p>
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
"""
        except proposals_mod.ProposalError as exc:
            plan_html = f"<h2>Dry-run preview</h2>{_errors_block(exc.errors)}"

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
<p><a class="button" href="/proposals">Back</a></p>
"""
    return 200, _layout(str(data.get("id")), body)


class StorygramServer(ThreadingHTTPServer):
    daemon_threads = True
    archive_root: Path
    provider_factory: Callable[[str, str], Provider] | None = None


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

    def _read_form(self) -> dict[str, list[str]]:
        length = int(self.headers.get("Content-Length", "0"))
        if length > MAX_BODY:
            raise ValueError("request body too large")
        raw = self.rfile.read(length).decode("utf-8")
        return parse_qs(raw, keep_blank_values=True)

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        path = unquote(parsed.path)
        if path == "/":
            self._send(200, render_home(self.root))
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
        if path.startswith("/proposals/"):
            proposal_id = path.removeprefix("/proposals/").strip("/")
            status, body = render_detail(self.root, proposal_id)
            self._send(status, body)
            return
        self._send(404, _layout("Not found", "<h1>Not found</h1>"))

    def do_POST(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        path = unquote(parsed.path)
        try:
            form = self._read_form()
        except ValueError as exc:
            self._send(413, _layout("Bad request", _errors_block([str(exc)])))
            return

        if path == "/proposals/generate":
            source = (form.get("source") or [""])[0]
            model = (form.get("model") or [""])[0].strip() or os.environ.get(
                "STORYGRAM_OLLAMA_MODEL", "llama3.2"
            )
            ollama_url = (form.get("ollama_url") or [""])[0].strip() or os.environ.get(
                "STORYGRAM_OLLAMA_URL", "http://127.0.0.1:11434"
            )
            if not source.strip():
                self._send(
                    400, render_generate_form(source, ["Source text is empty"], model, ollama_url)
                )
                return
            factory = cast(StorygramServer, self.server).provider_factory
            provider = (
                factory(model, ollama_url)
                if factory is not None
                else OllamaProvider(model=model, base_url=ollama_url)
            )
            try:
                data = LLMAdapter(provider).generate(self.root, source)
                save_pending(self.root, data)
            except LLMAdapterError as exc:
                self._send(
                    502,
                    render_generate_form(source, [str(exc)], model, ollama_url),
                )
                return
            generated_id = str(data["id"])
            self._redirect(f"/proposals/{quote(generated_id, safe='')}")
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
            errors = validate_mod.validate_instance(self.root, data, TYPE_BY_NAME["Proposal"])
            proposal_id = data.get("id")
            if not isinstance(proposal_id, str) or not proposal_id.startswith("proposal:"):
                errors.append("Proposal id must start with proposal:")
            if errors or not isinstance(proposal_id, str):
                self._send(400, _new_form(raw, errors))
                return
            if proposals_mod.find_proposal(self.root, proposal_id, include_applied=True):
                self._send(400, _new_form(raw, [f"Proposal already exists: {proposal_id}"]))
                return
            destination = proposals_mod.pending_dir(self.root) / proposals_mod.safe_filename(
                proposal_id
            )
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
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

        self._send(404, _layout("Not found", "<h1>Not found</h1>"))


def create_server(
    root: Path,
    host: str = "0.0.0.0",
    port: int = 8080,
    provider_factory: Callable[[str, str], Provider] | None = None,
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
