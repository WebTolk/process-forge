# Handoff: codex-main -> PF reviewer/operator

Objective: Complete live Codex-hook proof and independent review for the Ledger-centric Runtime/MCP slice.

Current status: Implementation and focused smokes passed; two external proofs remain pending.

Input artifacts:
- `.pf/artifacts/ledger-hooks-mcp-next-stage-20260814/baseline-audit.md`
- `.pf/artifacts/ledger-hooks-mcp-next-stage-20260814/implementation-report.md`
- `.pf/artifacts/ledger-hooks-mcp-next-stage-20260814/independent-review-waiver.md`

Files changed: Runtime Ledger routing, thin Codex adapter, stdio MCP facade, focused smoke, and EN/RU concept docs.

Files not to touch: daemon lifecycle semantics, platform-resolution work, and unrelated dirty worktree files.

Known issues: No installed active lifecycle hook configuration was available for a true client-generated `SessionStart`/`SessionEnd` test. The PF reviewer worker is prepared but has only a manual runtime driver.

Required checks: Run the focused smoke, then start and collect `ledger-hooks-mcp-next-stage-review` after configuring a permitted shell driver. For live proof, install a trusted documented Codex hook binding, restart a real client session, and compare Ledger/events before and after SessionStart and SessionEnd.

Next recommended action: Configure a project-trusted Codex hook binding from the documented syntax and a non-manual PF shell driver; do not substitute manual normalized event POSTs for those proofs.
