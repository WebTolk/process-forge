# docs111-mechanical Report

Timestamp: `2026-09-07 13:30:00 UTC`  
Task: `docs111-mechanical` (`docs-fix-1.1.1-20260907`)

## Scope executed (files changed)
- [docs/ru/concepts/resource-search-index.md](D:\Dev\process-forge\docs\ru\concepts\resource-search-index.md)
- [docs/concepts/assignment-front-matter.md](D:\Dev\process-forge\docs\concepts\assignment-front-matter.md)
- [docs/validation/validation.md](D:\Dev\process-forge\docs\validation\validation.md)

## D01 (RU search-index docs): completed
- Synced RU CLI examples to remove the unsupported `--project-root` flag from all five `search-index` commands:
  - `status`
  - `refresh`
  - `rebuild`
  - `doctor`
  - `tick`
- Updated `index_state` semantics to match EN:
  - Project snapshots do not own index documents.
  - Project snapshots do not create/duplicate Workplace index state.
  - Project snapshots only authorize queryable `resource_id` values.
- Updated `refresh` semantics:
  - No longer “refreshes current project snapshot” wording.
  - States it indexes registered Workplace resources/packages per `indexing.mode` and does **not** read project snapshot.
- Updated Runtime maintenance semantics:
  - It is Workplace-scoped.
  - It does not enumerate projects.
  - It does not depend on Runtime, Ledger, or active sessions.
- Preserved authorization language about project snapshots being needed for query authorization.

## D05 (assignment front matter): completed
- Changed `required_outputs` in sample to a mapping keyed by output id:
  - `example-report` now maps to:
    - `path: .pf/artifacts/example-report.md`
    - `type: markdown`
    - `required: true`

## D08 (validation/checks): completed
- Reworded Checksums section to start with:
  - “Checks the current public files against the existing deterministic SHA-256 inventory.”
- Kept explicit behavior:
  - `--check` (default when `--write` is not set) validates existing inventory.
  - `--write` generates/updates `checksums/processforge.sha256`.
- Added explicit note that checksum validation is public-file only and does **not** validate context/capsules.
- Added separate command guidance for context/capsule doctors only after confirming available CLI support:
  - `python bin/pf.py project-context-check --project-root <project-root> [--strict] [--json] [--session-start]`
  - `python bin/pf.py capsule-doctor --project-root <project-root> --capsule <capsule-path>`

## Required checks/results (captured)

1) Parser checks (no dispatch), with `sys.path.insert(0, 'tools')` before import:
- Command: `import processforge; parser = processforge.build_parser();`
- Parsed commands:
  - `search-index status --workplace X`
  - `search-index refresh --workplace X`
  - `search-index rebuild --workplace X`
  - `search-index doctor --workplace X`
  - `search-index tick --workplace X`
- All five parsed successfully and resolved to expected subcommands in namespace via `search_index_command`.

2) CLI help checks:
- `python bin/pf.py search-index -h` confirms valid subcommands exactly: `status/refresh/rebuild/doctor/tick`.
- `project-context-check --help` and `capsule-doctor --help` confirm required flags and options as documented.
- Confirmed current top-level command is not `checksums`; checksum validation is run via `python tools/validate-process-forge-checksums.py` (as already documented in file context).

3) Diff hygiene:
- `git diff --check -- docs/ru/concepts/resource-search-index.md docs/concepts/assignment-front-matter.md docs/validation/validation.md` returned no whitespace/merge-check errors.

## Residual risks
- RU doc still uses mixed Russian/English technical tokens (e.g., `resource_id`, `workplace`, `bounded`), which is consistent with existing style but may benefit of later style harmonization.
- Validation command section now includes doctor commands; it does not enumerate all optional flags for `project-context-check` beyond those shown in `--help` capture.