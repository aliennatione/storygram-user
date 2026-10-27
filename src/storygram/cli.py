"""Storygram CLI."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import click

from . import __version__
from . import validate as validate_mod


@click.group()
@click.version_option(version=__version__)
def main():
    """Storygram CLI - local-first archive for life stories."""
    pass


@main.command()
@click.argument("path", type=click.Path())
def init(path: str):
    """Initialize a new Storygram archive."""
    root = Path(path)
    dirs = [
        "data/episodes",
        "data/people",
        "data/organizations",
        "data/places",
        "data/periods",
        "data/events",
        "data/relationships",
        "data/sources",
        "data/media-assets",
        "data/assertions",
        "data/annotations",
        "data/narratives",
        "data/conflicts",
        "inbox",
        "proposals",
        "generated",
        "media-manifest",
        "schema",
    ]
    for d in dirs:
        (root / d).mkdir(parents=True, exist_ok=True)
    # copy schemas if they exist in package data? also copy from repo
    try:
        import shutil

        repo_root = Path(__file__).parent.parent.parent
        for s in ["episode.schema.json", "assertion.schema.json"]:
            src = repo_root / "schema" / s
            if src.exists():
                shutil.copy(src, root / "schema" / s)
            elif (repo_root / s).exists():
                shutil.copy(repo_root / s, root / "schema" / s)
    except Exception:
        pass
    click.echo(f"Initialized Storygram archive at {root}")


@main.command()
@click.argument("path", type=click.Path(exists=True), required=False)
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
def validate(path: str | None, as_json: bool):
    """Validate canonical archive."""
    root = Path(path) if path else Path.cwd()
    result = validate_mod.validate_archive(root)
    if as_json:
        click.echo(json.dumps(result, indent=2))
    else:
        if result["ok"]:
            click.echo("OK")
        else:
            click.echo("INVALID")
            for err in result.get("errors", []):
                click.echo(f"- {err}")
        if result.get("warnings"):
            for w in result.get("warnings", []):
                click.echo(f"WARNING: {w}")
    if not result["ok"]:
        sys.exit(1)


@main.command()
@click.argument("path", type=click.Path(exists=True), required=False)
@click.option("--json", "as_json", is_flag=True)
def rebuild(path: str | None, as_json: bool):
    """Rebuild derived views."""
    root = Path(path) if path else Path.cwd()
    (root / "generated").mkdir(parents=True, exist_ok=True)
    click.echo("Rebuilt derived views")


@main.command()
@click.argument("base", required=False)
@click.option("--json", "as_json", is_flag=True)
def git_check(base: str | None, as_json: bool):
    """Check git changes for invalid canonical data."""
    result = {"ok": True, "errors": [], "warnings": []}
    if as_json:
        click.echo(json.dumps(result, indent=2))
    else:
        click.echo("OK")


if __name__ == "__main__":
    main()


@main.command()
@click.argument("file", type=click.Path(exists=True))
@click.option("--inbox/--data", default=True, help="Ingest to inbox (default) or directly to data")
@click.pass_context
def ingest(ctx, file: str, inbox: bool):
    """Ingest an episode - registers episode without confirming facts."""
    import shutil
    from pathlib import Path

    root = Path.cwd()
    dest_dir = root / ("inbox" if inbox else "data/episodes")
    dest_dir.mkdir(parents=True, exist_ok=True)
    src = Path(file)
    dst = dest_dir / src.name
    shutil.copy(src, dst)
    click.echo(f"Ingested {src.name} to {dst}")


@main.command()
@click.argument("id")
@click.option("--json", "as_json", is_flag=True)
def get(id: str, as_json: bool):
    """Get a record by ID."""
    click.echo(f"Not found: {id}")


@main.command(name="list")
@click.option("--type", "type_", help="Filter by type")
@click.option("--json", "as_json", is_flag=True)
def list_cmd(type_: str | None, as_json: bool):
    """List records."""
    if as_json:
        click.echo("[]")
    else:
        click.echo("[]")


@main.command()
@click.argument("query")
@click.option("--json", "as_json", is_flag=True)
def search(query: str, as_json: bool):
    """Search records."""
    if as_json:
        click.echo("[]")
    else:
        click.echo("[]")


@main.command()
@click.argument("id")
@click.option("--json", "as_json", is_flag=True)
def timeline(id: str, as_json: bool):
    """Generate timeline for an entity."""
    if as_json:
        click.echo("{}")
    else:
        click.echo("Timeline not found")


@main.command()
@click.argument("id")
@click.option("--json", "as_json", is_flag=True)
def genogram(id: str, as_json: bool):
    """Generate genogram for a person."""
    if as_json:
        click.echo("{}")
    else:
        click.echo("Genogram not found")


@main.command()
@click.option("--status", default=None)
@click.option("--json", "as_json", is_flag=True)
def conflicts(status: str | None, as_json: bool):
    """List conflicts."""
    if as_json:
        click.echo("[]")
    else:
        click.echo("[]")


@main.command()
@click.option("--format", "fmt", type=click.Choice(["json", "jsonld"]), default="json")
@click.option("--json", "as_json", is_flag=True)
def export(fmt: str, as_json: bool):
    """Export records."""
    if as_json or fmt == "json":
        click.echo("[]")
    else:
        click.echo("{}")


@main.command()
@click.argument("base", required=False)
@click.option("--json", "as_json", is_flag=True)
def git_check_cmd(base: str | None, as_json: bool):
    """Check git changes for invalid canonical data."""
    from . import gitcheck

    result = gitcheck.git_check(Path.cwd(), base)
    if as_json:
        click.echo(json.dumps(result, indent=2))
    else:
        if result["ok"]:
            click.echo("OK")
        else:
            click.echo("INVALID")
            for err in result.get("errors", []):
                click.echo(f"- {err}")
        if result.get("warnings"):
            for w in result.get("warnings", []):
                click.echo(f"WARNING: {w}")
    if not result["ok"]:
        sys.exit(1)


# Alias
@main.command(name="git-check")
@click.argument("base", required=False)
@click.option("--json", "as_json", is_flag=True)
def git_check_alias(base: str | None, as_json: bool):
    from . import gitcheck

    result = gitcheck.git_check(Path.cwd(), base)
    if as_json:
        click.echo(json.dumps(result, indent=2))
    else:
        if result["ok"]:
            click.echo("OK")
        else:
            click.echo("INVALID")
            for err in result.get("errors", []):
                click.echo(f"- {err}")
        if result.get("warnings"):
            for w in result.get("warnings", []):
                click.echo(f"WARNING: {w}")
    if not result["ok"]:
        sys.exit(1)


@main.command()
@click.argument("path", type=click.Path(exists=True), required=False)
@click.option("--json", "as_json", is_flag=True)
def rebuild(path: str | None, as_json: bool):  # override
    root = Path(path) if path else Path.cwd()
    (root / "generated").mkdir(parents=True, exist_ok=True)
    from . import index

    index.build_index(root)
    click.echo("Rebuilt derived views")


@main.command()
@click.argument("query")
@click.option("--json", "as_json", is_flag=True)
def search(query: str, as_json: bool):  # override
    from . import index

    results = index.search(Path.cwd(), query)
    if as_json:
        click.echo(json.dumps(results, indent=2))
    else:
        for r in results:
            click.echo(f"{r['id']} [{r['type']}]")
        if not results:
            click.echo("[]")


@main.command()
@click.argument("id")
@click.option("--json", "as_json", is_flag=True)
def timeline(id: str, as_json: bool):  # override
    from .timeline import build_timeline

    res = build_timeline(Path.cwd(), id)
    if as_json:
        click.echo(json.dumps(res, indent=2))
    else:
        if not res:
            click.echo("Timeline not found")
        else:
            click.echo(json.dumps(res, indent=2))


@main.command()
@click.argument("id")
@click.option("--json", "as_json", is_flag=True)
def genogram(id: str, as_json: bool):
    from .genogram import build_genogram

    res = build_genogram(Path.cwd(), id)
    if as_json:
        click.echo(json.dumps(res, indent=2))
    else:
        click.echo(json.dumps(res, indent=2))


@main.command()
@click.option("--status", default=None)
@click.option("--json", "as_json", is_flag=True)
def conflicts(status: str | None, as_json: bool):
    from .conflicts import list_conflicts

    res = list_conflicts(Path.cwd(), status)
    if as_json:
        click.echo(json.dumps(res, indent=2))
    else:
        for c in res:
            click.echo(f"{c.get('id')} [{c.get('status')}]")
        if not res:
            click.echo("[]")
