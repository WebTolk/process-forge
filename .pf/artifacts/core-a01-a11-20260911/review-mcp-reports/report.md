# review-mcp-reports-report

## Verdict

Conditional pass. Two correctness findings remain.

## Findings

### P2 — Expected-report fingerprint bypasses safe path resolver

- File/lines: `tools/processforge.py:20895-20902`
- Scenario: A task’s `expected_report.artifact` is absolute, traverses upward, or points through a symlink. `task_verification_fingerprint()` constructs `project_root / normalize_assignment_path(expected_path)` and may call `is_file()`/`read_bytes()` without `project_output_path()`.
- Impact: `command_task_doctor` can read outside the project output scope, violating the single-resolver invariant.
- Acceptance: Resolve expected-report paths exclusively through `project_output_path`; invalid paths must be recorded as invalid/missing without filesystem reads. Add traversal, absolute, and symlink regression coverage.

### P2 — `oneOf` schema constraints are ignored by MCP validation

- File/lines: `tools/pf_runtime/mcp_server.py:291-319`
- Scenario: `tools/call` for `pf.work.transition` with `{"outcome":"ok","evidence":[3]}` is accepted and dispatched, although the advertised schema requires each evidence item to be a string or object.
- Impact: Invalid tool arguments reach business logic instead of returning `-32602`.
- Acceptance: Implement `oneOf` validation (or equivalent disjoint-branch validation) and prove invalid evidence items are rejected before dispatch, including notifications.

## Verified evidence

- Existing current artifacts report PASS for MCP validation, authenticated report content, exact session identity, classifier parity, and lifecycle identity.
- Static review confirms report authorization uses the safe resolver and exact-content/hash/provenance/session guards.
- Lifecycle startup/resume IDs are distinct and repeated identical resume payloads remain deduplicated.
- Symlink branch in `smoke_expected_report_containment` was skipped because symlink creation was unavailable.

## Test limitation

An additional disposable fixture probe was blocked by the first sandbox `PermissionError` while creating a temporary directory under `D:\temp`; no environment workaround was attempted.