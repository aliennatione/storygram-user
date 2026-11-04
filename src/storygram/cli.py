"""Storygram CLI."""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any, NoReturn

import click

from . import __version__
from . import proposals as proposals_mod
from . import validate as validate_mod
from .registry import RECORD_TYPES, find_schema


def _root(path: str | None) -> Path:
    return Path(path) if path else Path.cwd()


def _emit(data: Any, as_json: bool, plain: str | None = None) -> None:
    if as_json:
        click.echo(json.dumps(data, indent=2))
    elif plain is not None:
        click.echo(plain)
    else:
        click.echo(json.dumps(data, indent=2))


def _fail(message: str, as_json: bool = False) -> NoReturn:
    if as_json:
        click.echo(json.dumps({"ok": False, "errors": [message]}, indent=2))
    else:
        click.echo(message, err=True)
    raise SystemExit(1)


@click.group()
@click.version_option(version=__version__)
def main() -> None:
    """Storygram CLI - local-first archive for life stories."""


@main.command()
@click.argument("path", type=click.Path())
def init(path: str) -> None:
    """Initialize a new Storygram archive."""
    root = Path(path)
    for record_type in RECORD_TYPES:
        (root / "data" / record_type.directory).mkdir(parents=True, exist_ok=True)
    for directory in ("inbox", "proposals", "generated", "media-manifest", "schema"):
        (root / directory).mkdir(parents=True, exist_ok=True)

    copied = 0
    for record_type in RECORD_TYPES:
        destination = root / "schema" / record_type.schema_file
        candidate = find_schema(root, record_type)
        if candidate is not None and candidate.resolve() != destination.resolve():
            shutil.copy(candidate, destination)
            copied += 1
    click.echo(f"Initialized Storygram archive at {root} ({copied} schemas)")


@main.command()
@click.argument("path", type=click.Path(exists=True), required=False)
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
def validate(path: str | None, as_json: bool) -> None:
    """Validate canonical archive."""
    result = validate_mod.validate_archive(_root(path))
    if as_json:
        click.echo(json.dumps(result, indent=2))
    elif result["ok"]:
        click.echo("OK")
    else:
        click.echo("INVALID")
        for error in result.get("errors", []):
            click.echo(f"- {error}")
    if result.get("warnings"):
        for warning in result["warnings"]:
            click.echo(f"WARNING: {warning}")
    if not result["ok"]:
        raise SystemExit(1)


@main.command()
@click.argument("path", type=click.Path(exists=True), required=False)
@click.option("--json", "as_json", is_flag=True)
def rebuild(path: str | None, as_json: bool) -> None:
    """Rebuild the deterministic search index."""
    from . import index

    root = _root(path)
    errors: list[str] = []
    db_path = index.build_index(root, errors)
    output = {"ok": not errors, "index": str(db_path), "errors": errors}
    if as_json:
        click.echo(json.dumps(output, indent=2))
    else:
        for error in errors:
            click.echo(f"WARNING: {error}", err=True)
        click.echo(f"Rebuilt index at {db_path}")
        if errors:
            click.echo("Indexed valid records; malformed records were skipped", err=True)
    if errors:
        raise SystemExit(1)


@main.command(name="git-check")
@click.argument("base", required=False)
@click.option("--json", "as_json", is_flag=True)
def git_check(base: str | None, as_json: bool) -> None:
    """Check canonical records for missing or broken references."""
    from . import gitcheck

    result = gitcheck.git_check(Path.cwd(), base)
    if as_json:
        click.echo(json.dumps(result, indent=2))
    elif result["ok"]:
        click.echo("OK")
    else:
        click.echo("INVALID")
        for error in result.get("errors", []):
            click.echo(f"- {error}")
    if result.get("warnings"):
        for warning in result["warnings"]:
            click.echo(f"WARNING: {warning}")
    if not result["ok"]:
        raise SystemExit(1)


@main.group()
def ingest() -> None:
    """Capture source material without confirming facts."""


@ingest.command("episode")
@click.argument("file", type=click.Path(exists=True, dir_okay=False))
@click.option("--archive", "archive_path", type=click.Path(exists=True), default=None)
@click.option("--overwrite", is_flag=True, help="Replace an existing capture with the same name")
@click.option("--json", "as_json", is_flag=True)
def ingest_episode(file: str, archive_path: str | None, overwrite: bool, as_json: bool) -> None:
    """Copy an episode capture into inbox/ for later review.

    Ingestion writes a checksummed metadata sidecar under inbox/.storygram/ and
    never writes canonical data or confirms assertions.
    """
    from . import capture

    try:
        result = capture.ingest_capture(_root(archive_path), Path(file), overwrite=overwrite)
    except capture.CaptureError as exc:
        _fail(str(exc), as_json)
    if as_json:
        click.echo(json.dumps(result, indent=2))
        return
    click.echo(
        f"Ingested {result['filename']} to {Path(result['path']).parent} "
        f"({result['size']} bytes, sha256 {result['checksum']['value']})"
    )
    click.echo(f"Capture metadata: {result['metadata_path']}")


def _canonical_records(root: Path) -> list[dict[str, Any]]:
    items, errors = validate_mod.load_records(root)
    if errors:
        raise click.ClickException("; ".join(errors))
    return [data for _, data in items]


@main.command()
@click.argument("record_id")
@click.option("--archive", "archive_path", type=click.Path(exists=True), default=None)
@click.option("--json", "as_json", is_flag=True)
def get(record_id: str, archive_path: str | None, as_json: bool) -> None:
    """Get a canonical record by ID."""
    for record in _canonical_records(_root(archive_path)):
        if record.get("id") == record_id:
            _emit(record, as_json)
            return
    _fail(f"Not found: {record_id}", as_json)


@main.command(name="list")
@click.option("--type", "type_", help="Filter by type")
@click.option("--archive", "archive_path", type=click.Path(exists=True), default=None)
@click.option("--json", "as_json", is_flag=True)
def list_cmd(type_: str | None, archive_path: str | None, as_json: bool) -> None:
    """List canonical records."""
    records = _canonical_records(_root(archive_path))
    if type_:
        wanted = type_.lower()
        records = [
            record
            for record in records
            if str(record.get("type", "")).lower() == wanted
            or str(record.get("type", "")).lower().replace("asset", "-asset") == wanted
        ]
    if as_json:
        click.echo(json.dumps(records, indent=2))
        return
    for record in records:
        click.echo(f"{record.get('id')} [{record.get('type')}]")
    if not records:
        click.echo("[]")


@main.command()
@click.argument("query")
@click.option("--archive", "archive_path", type=click.Path(exists=True), default=None)
@click.option("--rebuild", is_flag=True, help="Force a full index rebuild before searching")
@click.option("--json", "as_json", is_flag=True)
def search(query: str, archive_path: str | None, rebuild: bool, as_json: bool) -> None:
    """Search canonical records."""
    from . import index

    results = index.search(_root(archive_path), query, rebuild=rebuild)
    if as_json:
        click.echo(json.dumps(results, indent=2))
        return
    for result in results:
        click.echo(f"{result['id']} [{result['type']}]")
    if not results:
        click.echo("[]")


def _record_exists(root: Path, record_id: str) -> bool:
    for path in (root / "data").rglob("*.json"):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if isinstance(data, dict) and data.get("id") == record_id:
            return True
    return False


@main.command()
@click.argument("record_id", required=False)
@click.option("--archive", "archive_path", type=click.Path(exists=True), default=None)
@click.option("--all", "all_records", is_flag=True, help="Build an archive-level timeline")
@click.option("--json", "as_json", is_flag=True)
def timeline(
    record_id: str | None, archive_path: str | None, all_records: bool, as_json: bool
) -> None:
    """Generate an entity, place, collection or archive timeline."""
    from .timeline import build_timeline

    if bool(record_id) == all_records:
        _fail("Provide either a record ID or --all", as_json)
    root = _root(archive_path)
    result = build_timeline(root, None if all_records else record_id)
    if not result:
        if all_records:
            if as_json:
                click.echo("[]")
            else:
                click.echo("No timeline entries in archive")
            return
        assert record_id is not None
        if _record_exists(root, record_id):
            if as_json:
                click.echo("[]")
            else:
                click.echo(f"No timeline entries for {record_id}")
            return
        _fail(f"Unknown record: {record_id}", as_json)
    _emit(result, as_json)


@main.command()
@click.argument("record_id")
@click.option("--archive", "archive_path", type=click.Path(exists=True), default=None)
@click.option("--json", "as_json", is_flag=True)
def genogram(record_id: str, archive_path: str | None, as_json: bool) -> None:
    """Generate an experimental genogram from relation:* assertions."""
    from .genogram import build_genogram

    result = build_genogram(_root(archive_path), record_id)
    if not as_json:
        for warning in result["warnings"]:
            click.echo(f"WARNING: {warning}", err=True)
    _emit(result, as_json)


@main.command()
@click.option("--status", default=None)
@click.option("--archive", "archive_path", type=click.Path(exists=True), default=None)
@click.option("--json", "as_json", is_flag=True)
def conflicts(status: str | None, archive_path: str | None, as_json: bool) -> None:
    """List explicit and assertion-derived conflicts."""
    from .conflicts import list_conflicts

    results = list_conflicts(_root(archive_path), status)
    if as_json:
        click.echo(json.dumps(results, indent=2))
        return
    for conflict in results:
        marker = " [derived]" if conflict.get("derived") else ""
        click.echo(f"{conflict.get('id')} [{conflict.get('status')}]{marker}")
        if conflict.get("derived"):
            click.echo(f"  assertions: {', '.join(conflict.get('assertions') or [])}")
    if not results:
        click.echo("[]")


@main.command()
@click.option(
    "--format",
    "fmt",
    type=click.Choice(["json", "jsonld", "yaml", "markdown"]),
    default="json",
)
@click.option("--visibility", multiple=True, help="Only export these visibility values")
@click.option("--archive", "archive_path", type=click.Path(exists=True), default=None)
@click.option("--json", "as_json", is_flag=True)
def export(fmt: str, visibility: tuple[str, ...], archive_path: str | None, as_json: bool) -> None:
    """Export canonical records."""
    from . import export as export_mod

    filters = set(visibility) if visibility else None
    root = _root(archive_path)
    try:
        if fmt == "jsonld":
            result: Any = export_mod.export_jsonld(root, filters)
        elif fmt == "yaml":
            result = export_mod.export_yaml(root, filters)
        elif fmt == "markdown":
            result = export_mod.export_markdown(root, filters)
        else:
            result = export_mod.export_json(root, filters)
    except export_mod.ExportError as exc:
        _fail(str(exc), as_json)
    if fmt in {"yaml", "markdown"}:
        click.echo(result)
    else:
        _emit(result, as_json)


@main.command(name="import")
@click.argument("file", type=click.Path(exists=True, dir_okay=False))
@click.option(
    "--format",
    "fmt",
    type=click.Choice(["json", "jsonld", "yaml", "markdown"]),
    default=None,
    help="Export format; inferred from the file suffix when omitted",
)
@click.option("--id", "proposal_id", default=None, help="Pending proposal ID")
@click.option("--title", default=None, help="Pending proposal title")
@click.option(
    "--evidence",
    multiple=True,
    help="Canonical Episode/Source/Annotation ID used as evidence for imported records",
)
@click.option("--archive", "archive_path", type=click.Path(exists=True), default=None)
@click.option("--json", "as_json", is_flag=True)
def import_cmd(
    file: str,
    fmt: str | None,
    proposal_id: str | None,
    title: str | None,
    evidence: tuple[str, ...],
    archive_path: str | None,
    as_json: bool,
) -> None:
    """Import an export as a pending proposal without writing canonical data."""
    from . import importer

    try:
        result = importer.import_records(
            _root(archive_path),
            Path(file),
            fmt=fmt,
            proposal_id=proposal_id,
            title=title,
            evidence=list(evidence),
        )
    except importer.ImportError as exc:
        _fail(str(exc), as_json)
    if as_json:
        click.echo(json.dumps(result, indent=2))
        return
    click.echo(f"Imported {result['records']} record(s) into {result['proposal_id']}")
    click.echo(f"Pending proposal: {result['path']}")
    click.echo(f"Next: storygram proposal approve {result['proposal_id']} --dry-run")


@main.command()
@click.option("--host", default="0.0.0.0", show_default=True)
@click.option("--port", default=8080, type=int, show_default=True)
@click.option("--archive", "archive_path", type=click.Path(exists=True), default=None)
def web(host: str, port: int, archive_path: str | None) -> None:
    """Serve the local proposal review UI."""
    from .web import serve

    serve(_root(archive_path), host, port)


@main.group()
def proposal() -> None:
    """Create, inspect, approve or reject proposals."""


@proposal.command("new")
@click.option("--file", "file_", type=click.Path(exists=True), required=True)
@click.option("--archive", "archive_path", type=click.Path(exists=True), default=None)
@click.option("--json", "as_json", is_flag=True)
def proposal_new(file_: str, archive_path: str | None, as_json: bool) -> None:
    """Register a pending proposal from a JSON file."""
    root = _root(archive_path)
    try:
        data = json.loads(Path(file_).read_text(encoding="utf-8"))
    except Exception as exc:
        _fail(f"Cannot read proposal: {exc}", as_json)
    if not isinstance(data, dict):
        _fail("Proposal must be a JSON object", as_json)
    try:
        destination = proposals_mod.create_pending(root, data)
    except proposals_mod.ProposalError as exc:
        _fail("; ".join(exc.errors), as_json)
    _emit(
        {"ok": True, "proposal_id": data["id"], "path": str(destination)},
        as_json,
    )


@proposal.command("generate")
@click.option("--file", "file_", type=click.Path(exists=True), default=None)
@click.option("--text", default=None)
@click.option(
    "--provider",
    default=None,
    help="Ollama or OpenAI-compatible provider; default $STORYGRAM_LLM_PROVIDER or ollama",
)
@click.option("--model", default=None, help="Model name; default $STORYGRAM_LLM_MODEL")
@click.option("--url", "base_url", default=None, help="LLM base URL; default $STORYGRAM_LLM_URL")
@click.option(
    "--ollama-url", "legacy_url", default=None, help="Deprecated alias for --url (Ollama only)"
)
@click.option(
    "--api-key",
    default=None,
    envvar="STORYGRAM_LLM_API_KEY",
    help="Bearer token for OpenAI-compatible providers; prefer the env var",
)
@click.option("--archive", "archive_path", type=click.Path(exists=True), default=None)
@click.option("--no-save", is_flag=True, help="Print the proposal without saving it")
@click.option("--json", "as_json", is_flag=True)
def proposal_generate(
    file_: str | None,
    text: str | None,
    provider: str | None,
    model: str | None,
    base_url: str | None,
    legacy_url: str | None,
    api_key: str | None,
    archive_path: str | None,
    no_save: bool,
    as_json: bool,
) -> None:
    """Generate a pending proposal with a local or OpenAI-compatible model."""
    from .llm import (
        LLMAdapter,
        LLMAdapterError,
        provider_config,
        provider_from_config,
        save_pending,
    )

    if file_ and text:
        _fail("Use either --file or --text, not both", as_json)
    if file_:
        source = Path(file_).read_text(encoding="utf-8")
    elif text:
        source = text
    else:
        _fail("Provide --file or --text", as_json)
    resolved_provider = provider or ("ollama" if legacy_url and not base_url else None)
    try:
        config = provider_config(resolved_provider, model, base_url or legacy_url, api_key)
    except LLMAdapterError as exc:
        _fail(str(exc), as_json)
    root = _root(archive_path)
    adapter = LLMAdapter(provider_from_config(config))
    try:
        proposal_data = adapter.generate(root, source)
        path = None if no_save else save_pending(root, proposal_data)
    except LLMAdapterError as exc:
        _fail(str(exc), as_json)
    output = {"ok": True, "proposal": proposal_data, "path": str(path) if path else None}
    _emit(output, as_json)


@proposal.command("list")
@click.option("--all", "include_applied", is_flag=True, help="Include merged/archive proposals")
@click.option("--archive", "archive_path", type=click.Path(exists=True), default=None)
@click.option("--json", "as_json", is_flag=True)
def proposal_list(include_applied: bool, archive_path: str | None, as_json: bool) -> None:
    """List pending proposals."""
    root = _root(archive_path)
    entries = []
    for path, data in proposals_mod.list_proposals(root, include_applied=include_applied):
        try:
            label = str(path.relative_to(root))
        except ValueError:
            label = str(path)
        entries.append(
            {
                "id": data.get("id"),
                "status": data.get("status"),
                "title": data.get("title"),
                "operations": len(data.get("operations") or []),
                "path": label,
            }
        )
    if as_json:
        click.echo(json.dumps(entries, indent=2))
        return
    for entry in entries:
        click.echo(f"{entry['id']} [{entry['status']}] {entry['operations']} op(s) {entry['path']}")
    if not entries:
        click.echo("[]")


@proposal.command("show")
@click.argument("proposal_id")
@click.option("--archive", "archive_path", type=click.Path(exists=True), default=None)
def proposal_show(proposal_id: str, archive_path: str | None) -> None:
    """Show a pending or applied proposal."""
    root = _root(archive_path)
    path = proposals_mod.find_proposal(root, proposal_id, include_applied=True)
    if path is None:
        _fail(f"Proposal not found: {proposal_id}")
    click.echo(path.read_text(encoding="utf-8"))


@proposal.command("approve")
@click.argument("proposal_id")
@click.option("--archive", "archive_path", type=click.Path(exists=True), default=None)
@click.option("--dry-run", is_flag=True, help="Plan only; write nothing")
@click.option("--no-commit", is_flag=True, help="Write canonical data without Git commit")
@click.option("--json", "as_json", is_flag=True)
def proposal_approve(
    proposal_id: str, archive_path: str | None, dry_run: bool, no_commit: bool, as_json: bool
) -> None:
    """Validate and apply a proposal atomically."""
    try:
        result = proposals_mod.apply_proposal(
            _root(archive_path),
            proposal_id,
            dry_run=dry_run,
            commit=not no_commit,
        )
    except proposals_mod.ProposalError as exc:
        _fail("; ".join(exc.errors), as_json)
    if as_json:
        click.echo(json.dumps(result, indent=2))
        return
    if dry_run:
        click.echo(f"DRY RUN {proposal_id}")
    else:
        click.echo(f"Applied {proposal_id}")
    for operation in result["operations"]:
        click.echo(
            f"- {operation['op']} {operation['record_type']} "
            f"{operation.get('record_id') or operation.get('target_id') or ''}".rstrip()
        )
    for path in result["files"]:
        click.echo(f"  {path}")
    if result.get("commit"):
        click.echo(f"Committed {result['commit']}")


@proposal.command("reject")
@click.argument("proposal_id")
@click.option("--archive", "archive_path", type=click.Path(exists=True), default=None)
@click.option("--reason", default=None)
@click.option("--json", "as_json", is_flag=True)
def proposal_reject(
    proposal_id: str, archive_path: str | None, reason: str | None, as_json: bool
) -> None:
    """Reject a pending proposal without changing canonical data."""
    try:
        result = proposals_mod.reject_proposal(_root(archive_path), proposal_id, reason)
    except proposals_mod.ProposalError as exc:
        _fail("; ".join(exc.errors), as_json)
    _emit(result, as_json, f"Rejected {proposal_id}")


@proposal.command("withdraw")
@click.argument("proposal_id")
@click.option("--archive", "archive_path", type=click.Path(exists=True), default=None)
@click.option("--reason", default=None)
@click.option("--json", "as_json", is_flag=True)
def proposal_withdraw(
    proposal_id: str, archive_path: str | None, reason: str | None, as_json: bool
) -> None:
    """Withdraw a pending proposal without changing canonical data."""
    try:
        result = proposals_mod.withdraw_proposal(_root(archive_path), proposal_id, reason)
    except proposals_mod.ProposalError as exc:
        _fail("; ".join(exc.errors), as_json)
    _emit(result, as_json, f"Withdrew {proposal_id}")


if __name__ == "__main__":
    main()
