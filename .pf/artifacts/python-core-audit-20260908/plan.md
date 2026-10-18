# Python core audit — 2026-09-08

Status: completed. Owner: primary agent, single-agent task-batch-execution.
Run: garage-audit-current-processforge-python-core-and-codebase-for-reproduci
Assignment: audit-current-processforge-python-core-and-codebase-for-reproducible-cor
Baseline: dev, HEAD 1aecc18b6824204ca45ab30241b92d26e6d583a5 plus existing uncommitted required-output and documentation changes.

## Boundary

Audit current working-tree behavior. No product edits, commits, publishing, installed-Core changes or repairs to old runs. Writes: this audit's .pf artifacts, logs, review, handoff, private reproduction helpers, and ordinary governed state. Keep earlier evidence and immutable capsules intact.

## Sequential work

1. Read current PF context, assignment, capsule and recent handoff; record initial working-tree status and source inventory.
2. Inspect Python architecture and static correctness: CLI, extracted services, runtime adapters and existing smoke coverage.
3. Exercise process transitions and evidence validation; local search authorization, freshness and reconciliation; core update/rollback and persistence boundaries. Reproductions use isolated temporary fixtures.
4. Run relevant existing checks and independently adjudicate each suspected issue. Separate confirmed defects, known test-fixture failures and design risks.
5. Produce prioritized findings with file/line references, trigger, observed/expected behavior, remediation guidance, validation scope, review and final handoff. Complete this audit's PF run.

## Tooling and current context

IDE MCP is open on another project; Serena symbol lookup fails because active languages are empty. Python AST and bounded reads are the fallback. No Python shared toolchain is available and the snapshot selects no platform; use the repository's Python validation commands. MCP work-start remains snapshot_not_fresh after a successful local CLI refresh; local CLI created the scoped audit run. Investigate the source/installed-service mismatch without restarting infrastructure.

Earlier sessionless-search failure is historical evidence until rerun. Full release qualification is outside this analysis-only audit.
