# Resume Instructions for Storygram

This file is a short pointer for resuming work. The maintained working memory is:

- `AGENTS.md` - workflow, environment and safety rules.
- `docs/dev/STATE.md` - current branch, completed work, checks and exact next steps.
- `docs/dev/HANDOFF.md` - compact brief for the next session.
- `docs/dev/DECISIONS.md`, `LESSONS.md`, `AUDIT.md` - rationale, quirks and history.

## Quick Resume

```bash
cd /data
git status --short
PYTHONPATH=/data/src python -m pytest -q
PYTHONPATH=/data/src python -m storygram --help
```

The repository persists on host storage. Do not rely on chat history; read the files above before changing code.

## Current Handoff

Container runtime verification is complete through the host Docker socket (Podman Engine 5.8.2 via its Docker-compatible API): image build, non-root start, auto-init, healthcheck, in-container proposal flow, named-volume persistence and host bind mount all passed. The next work unit is the legacy-surface audit; see `docs/dev/HANDOFF.md`. Do not start Docker-in-Docker and do not mount the socket into the Storygram application container.

## Historical Files

`PLAN_EXECUTION.md` and `AI_IMPLEMENTATION_PROMPT.md` are original implementation prompts. `PRD.md` remains the product authority. They are historical context, not current status.
