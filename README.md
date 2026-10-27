# Storygram

Local-first, versionable archive for episodes, sources, people, places, events, relationships, assertions, conflicts and narratives. The core works offline without LLMs.

## Layout
- `data/` canonical reviewed records
- `inbox/` unreviewed imports
- `proposals/` proposed changes awaiting review
- `media-manifest/` checksummed media manifests
- `generated/` reproducible derived views
- `schema/` JSON schemas

## Quickstart
```bash
pip install -e ".[dev]"
storygram init ./archive
storygram validate ./archive
PYTHONPATH=/data/src python -m pytest -v
```

## Documentation
- [English docs](docs/en/)
- [Documentazione italiana](docs/it/)
- [README (Italiano)](README.it.md)

## Philosophy
- Episode is not a fact; assertions are propositions with evidence
- Bitemporality (`valid_time` / `transaction_time`)
- Conflicts explicit, never auto-resolved
- Correction history preserved via supersession
- Deterministic core, no AI required
