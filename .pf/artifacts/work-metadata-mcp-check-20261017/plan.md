# План и журнал проверки MCP fixture

## 2026-10-17 17:49:05 UTC - primary / executor

Task: узкая адаптация одной existing MCP snapshot fixture к optional metadata provider основной Work. Это не subagent; один primary последовательно обслуживает два непересекающихся scope. Родитель владеет исходниками, эта поддерживающая Work — только tools/smoke_garage_snapshot_read_composition.py и собственными артефактами. Capsule/assignment/exact state прочитаны, context valid/ready; общий проектный контекст fresh/Forge. Отдельная Work нужна потому, что этот existing test не входил в основной write scope. Scope основного задания не расширялся.

Files analyzed: targeted GarageSnapshotTests.test_mcp_factory_after_guards_and_existing_projection и context_payload test, CurrentWork factory/MCP call site, pinned metadata architecture и основной pre-code plan.
Artifacts changed: настоящий журнал/план и дальнейший report.
Templates used: pinned software-feature-development stage obligations.
Tools used: PF MCP, Serena, native existing Python smoke.

Brief/scope: test fixture factory currently accepts only three positional arguments. The approved source adds optional keyword work_metadata for shared pass; adapt that fixture to accept it and verify the bound project when supplied. Keep every guard/error, call-count, projection and cleanup assertion. No other test expectations, source or public contract changes.

Investigation: original Git snapshot passes all 8 tests. Current implementation revealed one genuine source integration issue (passing an unnecessary None keyword to the ordinary CurrentWorkService constructor); the primary corrected it in the original authorized source scope. This task changes only the fixture signature and asserts the optional pass belongs to the supplied root. Domain: test injection seam, not a user-facing API or new runtime rule.

Architecture/plan: add keyword-only work_metadata=None to the local factory; if supplied, inspect only the bound project_root of its lazy pass. This assertion performs no document I/O. Existing old caller paths remain testable without the keyword. Run all 8 existing tests after patch, inspect diff, close and deliver only owned file/artifacts in a separate commit to both dev remotes. The primary's uncommitted source remains untouched.

Risks: this is supporting assurance, not independent acceptance of the main optimization. Main source parity, full handler measurements and checksum remain with the primary Work. Release profile not_applicable for a test-only change; no service operations.
Next steps: native stage advance to implementation, apply minimal fixture patch, run existing complete smoke, review/closeout/commit+both readbacks. Handoff to main metadata implementation after completion.
