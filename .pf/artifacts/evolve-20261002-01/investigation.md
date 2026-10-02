# Investigation: evolve-20261002-01

Findings:
- `work-start --scope-file` validates the scope JSON and builds the future context before writing durable Work records.
- Before this change, `_start_locked` checked `execution_contract.readiness`, overlap and malformed scope, but did not run `permission_readiness` until later `work_state`.
- As a result, an explicit scope that omitted `execution_mode` inherited the default implementation mode, but could manually omit `write_product`; the Work could be published and only then report `product_write_scope_missing`.
- `tools/processforge.py` only forwards `--scope-file` into `ProcessExecutionService.start`; it did not need a write in this scoped Work.

Impact:
- The fix is limited to explicit local operator scope creation before `_write_capsule`.
- Invalid or permission-unready explicit scopes now return `blocked/work_scope_not_ready` with `execution_readiness` details and leave no Run, Assignment, or capsule behind.
- Existing successful implementation scopes and planning/artifact-only scopes continue to work.
- Existing unscoped ProcessExecution fixture behavior was checked with `tools/smoke_process_execution_integrity.py`.

Python/PF knowledge used:
- `docs.python:root` and `docs.python-practices:root` resolved through PF before Python implementation.
- Python changes use local exception handling and assertions consistent with existing smoke style.

Validation so far:
- `python -X utf8 -m py_compile src/processforge_core/process_execution.py src/processforge_core/continuation.py tools/smoke_work_start_scope.py`
- `python -X utf8 -B tools/smoke_work_start_scope.py`
- `python -X utf8 -B tools/smoke_process_execution_integrity.py`
- `git diff --check -- <changed files>` passed with only a CRLF/LF normalization warning for `src/processforge_core/process_execution.py`.
