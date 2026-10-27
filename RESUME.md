# Resume Instructions for Storygram

This file contains all information needed to resume work if the container is destroyed. /data is bind-mounted to host storage and persists.

## Current State
- Project bootstrapped with CLI, schemas (Episode, Assertion), validation, models
- Tests passing (8 tests)
- Git repo initialized on branch main
- Documentation bilingual (README EN/IT, CONTRIBUTING EN/IT)
- Plan saved in PLAN.md

## Quick Resume
```bash
cd /data
pip install --break-system-packages -e ".[dev]"  # if needed
PYTHONPATH=/data/src python -m pytest -v
PYTHONPATH=/data/src python -m storygram --help
```

## Git State
- Initialize if .git missing: `git init && git branch -M main`
- Current branch: check `git -C /data branch -v`

## Next Steps (see PLAN.md)
Follow milestones M0-M8 as documented. Start from next unfinished milestone.

## Key Files
- PLAN.md - complete implementation plan
- AGENTS.md - general rules
- PRD.md - product requirements
- AI_IMPLEMENTATION_PROMPT.md - original prompt
- schema/*.json - JSON schemas
- src/storygram/ - source code
- tests/ - tests and fixtures

## Environment
- Python 3.14, Alpine Linux
- Dependencies installed system-wide with --break-system-packages
