# A11 hooks report

## Result

Implemented the bounded SessionStart lifecycle identity repair.

- `tools/pf_runtime/codex_hooks.py`
  - Separates non-startup SessionStart lifecycle facts deterministically.
  - Preserves startup and PostToolUse ID semantics.
  - Preserves provider-supplied IDs.
  - Repeated resume payloads remain idempotent; identical occurrences without provider identity cannot be distinguished.

- `tools/smoke_codex_lifecycle_identity.py`
  - Added normalized and real host-ingest regression coverage.

## Verification

- PASS: Python compilation.
- PASS: normalization assertions.
- UNEXECUTED: Full smoke blocked by Windows `PermissionError` (`WinError 5`) creating the temporary fixture. No workaround was attempted per instructions.

No dispatcher or global retry behavior was changed.