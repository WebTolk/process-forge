# Run Summary: ProcessForge full machine acceptance

- run_id: `pf-machine-acceptance-20260829`
- status: `completed`

## Tasks

- `pf-machine-baseline-audit-20260829`: `done` - Recovered from shell-worker launcher WinError 2: existing baseline artifact and direct machine verification supplied the required evidence.
- `pf-release-surface-audit-20260829`: `done` - Collected worker run output from codex-exec
- `pf-release-candidate-hardening-20260829`: `done` - Qualified local 1.2.1 candidate; public checks and full extracted archive suite pass.
- `pf-isolated-update-matrix-20260829`: `done` - Spark worker completed the mechanical update matrix; its direct report is retained as transition evidence. Independent target-side 1.2.1 review provides the authoritative updater acceptance because 1.1.0 did not have the final updater.
- `pf-installed-upgrade-acceptance-20260829`: `done` - Final 1.2.1 archive passed full extracted tests and installed through target-side updater.
- `pf-telemetry-evidence-review-20260829`: `done` - Verified PF events, chat, telemetry, native hooks and Agent Ledger lifecycle.
- `pf-final-restoration-review-20260829`: `done` - Exact 1.1.0 restoration verified; Runtime and standalone MCP restarted; acceptance passed with documented conditions.
- `pf-worker-env-secret-redaction-20260829`: `done` - Prevented inherited host environment values from being persisted in worker command state; added and passed focused regression; confirmed codex-exec workers launch with launch-time inheritance.
- `pf-machine-orchestration-20260829`: `done` - Machine acceptance matrix, append-only journal and final handoff completed.
- `pf-public-cleanliness-remediation-20260829`: `done` - Removed machine-local and platform-specific data from public Garage smokes; all affected smokes and public cleanliness now pass.
- `pf-search-resolver-consistency-20260829`: `done` - Unified maintenance, Garage, and session-context search resolution; focused regressions pass in source and candidate.
- `pf-target-updater-review-20260829`: `done` - Target-side 1.2.1 updater passed isolated update, local-modification blocking, forced rollback, corrupt archive, repair classification, and exact 1.1.0 checksum restoration.
- `pf-runtime-status-timeout-remediation-20260829`: `done` - Fixed real Runtime status starvation and full-journal scan; focused and long-lived smokes pass, final 1.2.1 archive rebuilt, installed, and returns ready under scheduler load.
- `pf-joomla-agent-acceptance-20260829`: `done` - Governed agent delivered and independently verified a real Joomla 6 plugin and frontend behavior.
- `pf-codex-worker-governance-remediation-20260829`: `done` - Enforced assignment sandbox, PF-first MCP, disabled memories, MCP approval and safe PF-only hook trust.
- `pf-mcp-codex-contract-remediation-20260829`: `done` - Delivered bounded Codex-compatible MCP context and real stdio contract coverage.
