# Implementation: evolve-20261002-01

Changed product files:
- `src/processforge_core/process_execution.py`
- `tools/smoke_work_start_scope.py`
- `docs/concepts/work-context.md`
- `docs/ru/concepts/work-context.md`

Change summary:
- `ProcessExecutionService._start_locked` now runs `permission_readiness` on the future normalized scope and execution mode before `_write_capsule`.
- A permission-unready explicit scope returns `blocked/work_scope_not_ready` with `execution_readiness` details before publishing Run, Assignment or capsule records.
- `tools/smoke_work_start_scope.py` now covers:
  - implicit implementation with missing `write_product`;
  - empty grants;
  - contradictory allowed/forbidden actions;
  - docs/read-only style write-product denial;
  - positive `planning_only` artifact scope without `write_product`;
  - no-publication invariants for rejected declarations.
- EN/RU docs now describe effective permission preflight and safe retry after timeout.

Scope respected:
- No writes to `tools/processforge.py`.
- No infrastructure install/restart/update.
- No old capsules or unrelated active Work mutated.

Initial validation:
- `py_compile`: pass.
- `smoke_work_start_scope.py`: pass.
- `smoke_process_execution_integrity.py`: pass.
- `git diff --check` on changed files: pass, with a CRLF/LF normalization warning only.
