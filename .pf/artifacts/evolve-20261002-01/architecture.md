# Architecture Plan: evolve-20261002-01

Architecture:
- Keep `ProcessExecutionService.start()` as the single Work creation contract.
- After applying `scope_intent` and building the future context fields, run `permission_readiness` on the normalized scope and assignment execution mode.
- Return `blocked/work_scope_not_ready` before `_write_capsule` when permission readiness is not `ready`.
- Include `execution_readiness` in the blocked payload so callers can report the precise missing grant.

Implementation plan:
1. Add pre-publication permission readiness check in `src/processforge_core/process_execution.py`.
2. Extend `tools/smoke_work_start_scope.py` with:
   - implicit implementation missing `write_product`;
   - planning-only artifact scope success;
   - docs-only/read-only/empty/contradictory cases;
   - no-publication assertions via the existing `records()` guard.
3. Update EN/RU `work-context` documentation for effective permission readiness and timeout retry guidance.
4. Run targeted compile/smoke/diff checks.

Decision log:
- Do not duplicate permission rules: reuse `permission_readiness`.
- Do not edit `tools/processforge.py`: it already delegates to Core and is outside this Work's write scope.
- Do not broaden existing Work/capsules: blocked explicit scopes leave no durable records.
