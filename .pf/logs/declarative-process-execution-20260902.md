# Declarative Process Execution Log

## 2026-09-02 10:58 - primary-agent

Task: Audit and design universal declarative Process execution.
Files changed: none in product code.
Artifacts changed: current-state audit, YAML capability map, service design, transition contract.
Templates used: none.
Tools used: pf.context, project-context-refresh, pf.work.start, ProcessForge CLI, Serena, rg.
Decisions: use a universal injected-core service; keep process transitions separate from stage transitions; preserve low-level CLI.
Risks: project snapshot immediately returns to stale; current assignment has declared overlap with blocked historical release work.
Next steps: implement service, adapters, schema changes, projections, and focused smokes.
Handoff: none.

## 2026-09-02 11:45 - primary-agent

Task: Implement, independently review, harden and externally accept declarative Process execution.
Files changed: ProcessExecutionService, Garage/MCP/host/CLI adapters, Process/Run/Assignment/Event schemas, agent guidance, concepts, focused smokes and release command registry.
Artifacts changed: capability/design/transition reports, event/projector report, workflow report, two independent reviews and external acceptance report.
Delegation: Codex architecture reviewer, Codex code reviewer and PF `codex-exec` shell reviewer; all reports were collected. The shell worker initially lacked a model parameter, then completed with `gpt-5.4`.
Verification: 11 requested smokes, integrity smoke, MCP contract, stage projector, stage contract normalization and governed stage resolution passed after remediation. A final external Joomla-project run completed all nine stages exclusively through the public work API.
Decisions: invalid pins fail closed; public callers cannot choose stage; output artifacts needed by later stages remain required; finalization preserves evidence/history when completion is blocked; legacy summary/completion commands share per-Run locks.
Risks: the earlier 1.1.0 release run remains blocked by its separate derived-artifact consistency finding; the working tree already contains unrelated historical changes; multi-file persistence is serialized and atomic per file but is not a database transaction.
Next steps: full release-test, checksum inventory refresh, final validation artifact and task/run disposition.

## 2026-09-02 12:15 - primary-agent

Task: Final verification and handoff.
Status: implementation and shell-review assignments completed; the tracking Run remains in progress because it was created through legacy bootstrap before the declarative service existed, and it must not be manually completed through the normal public workflow.
Verification: full release-test executed for 1238.47 seconds. New declarative tests passed; schema validation was subsequently repaired and re-run successfully, with checksum verification passing.
Residual release blockers: release archive provenance requires a clean Git tree; trailing whitespace remains in a historical context snapshot; public 1.1.0 is independently blocked by the pre-existing run-artifact consistency remediation.
