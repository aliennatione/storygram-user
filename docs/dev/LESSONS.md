# Lessons and Quirks

- Existing tests assume `/data` is the working directory.
- `schema/*.schema.json` and root-level `*.schema.json` are duplicates. Update both.
- `cli.py` registers several commands twice; Click uses the last definition. Edit the later one and deduplicate when touching the file.
- `validate` historically checked only Episodes and Assertions and never called referential integrity. The new validation module covers every type.
- `init` still copies only two schemas; fix it before relying on fresh archives.
- `proposals/` is ignored, so pending proposals are local-only. `data/proposals/` is the canonical merged archive and must be committed.
- Assertion supersession previously required `supersedes` on the superseded record. The correct invariant is a closed `transaction_time.recorded_until`; the replacement carries `supersedes`.
- `episode_type` has a fixed enum; use `other` when a fixture is not a real capture type.
- Full-repo ruff and mypy failures pre-date this work. Fix files being touched; do not hide the remaining debt.
- `apply_proposal` rejects a dirty tracked tree before writing. Commit application code in the main repository before manually approving proposals there.
- Atomic writes use same-directory temp files and `os.replace`; rollback restores prior bytes or removes newly created files.
- The archive commit is path-scoped, so unrelated untracked files are not included.
- Playwright and browser binaries are not installed yet.
