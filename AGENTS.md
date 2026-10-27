# AGENTS.md

## Purpose

This file contains general engineering instructions for human contributors and AI coding agents. Project-specific requirements belong in `PRD.md`, project documentation, and task-specific prompts.

## Before editing

1. Inspect the repository, Git status, and existing build system.
2. Read `README.md`, `PRD.md`, relevant documentation, and nearby code/tests.
3. Run the existing checks before making changes and record pre-existing failures.
4. Identify the smallest complete change that satisfies the task.
5. State a concise plan before significant implementation work.

## Engineering principles

- Prefer simple, explicit, maintainable solutions.
- Preserve existing behavior unless a change is required.
- Keep changes focused, reversible, and reviewable.
- Separate domain logic, persistence, presentation, and integrations.
- Validate input at system boundaries.
- Make invalid states visible and actionable.
- Prefer deterministic behavior over hidden heuristics.
- Do not invent missing information; represent uncertainty explicitly.
- Do not silently overwrite, discard, or migrate user data.
- Avoid unnecessary dependencies and premature abstractions.

## Repository hygiene

- Never commit secrets, credentials, private keys, tokens, or unapproved personal data.
- Do not edit generated files manually when they are reproducible.
- Keep temporary files outside the repository or remove them before completion.
- Use the repository's encoding, line endings, naming, and formatting conventions.
- Keep public identifiers stable once released.
- Update documentation when public behavior, schemas, APIs, configuration, or workflows change.

## Code quality

- Follow the project's formatter, linter, and type-checking conventions.
- Use descriptive names and small functions with clear responsibilities.
- Avoid broad exception handling that hides failures.
- Return errors containing the relevant operation, object, file, or field.
- Keep external systems behind explicit adapters.
- Preserve backward compatibility where promised.
- Document compatibility impact for schema, API, database, or file-format changes.

## Testing

Every meaningful change should have appropriate tests:

- unit tests for pure logic;
- integration tests for component boundaries;
- regression tests for fixed defects;
- malformed-input and validation tests;
- end-to-end tests for critical workflows.

Test normal, empty, missing, malformed, ambiguous, boundary, and failure cases as appropriate. Do not remove or weaken tests merely to obtain a passing suite.

Before reporting completion, run the relevant project checks, normally:

```text
format check
lint
static/type check
unit tests
integration tests
build/package check
```

Report the exact commands and results.

## Data safety

- Prefer archive, deprecation, or versioned replacement over deletion.
- Require a dry-run or explicit confirmation for destructive operations.
- Preserve provenance when transforming or importing data.
- Do not make automated changes to external systems without the project's approved workflow.
- Use synthetic data in tests unless real data is explicitly authorized.

## AI-agent conduct

AI agents must:

- distinguish facts, requirements, assumptions, and proposals;
- ask clarification only when conservative progress is impossible;
- never claim a check passed without running it;
- disclose failed commands and known limitations;
- avoid unrelated refactoring;
- produce reviewable diffs for data or schema changes;
- surface security, privacy, compatibility, and migration risks.

## Completion report

Use this format after each work unit:

```text
## Summary
- ...

## Files changed
- ...

## Checks run
- `command`: result

## Assumptions
- ...

## Risks or limitations
- ...

## Next step
- ...
```

## Priority

When instructions conflict, use this order:

1. system and user instructions;
2. security, privacy, and data integrity;
3. explicit project requirements in `PRD.md`;
4. existing compatibility commitments;
5. maintainability and simplicity;
6. optimization and convenience.
