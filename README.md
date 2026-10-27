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
uv pip install -e ".[dev]"
storygram init ./archive
storygram validate ./archive
```

## Languages / Lingue
- [English](README.md)
- [Italiano](README.it.md)
