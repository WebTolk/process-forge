# Runtime/MCP autostart and documentation audit log

## 2026-08-29 14:58 - orchestrator

Task: Audit Runtime/MCP documentation and decide Windows startup ownership.
Files changed: `.pf/adr/runtime-mcp-windows-autostart.md`, documentation audit artifacts.
Artifacts changed: audit, retry audit, architecture ADR.
Templates used: ProcessForge software-feature-development run/task flow.
Tools used: Serena targeted search, shell fallback, PF worker-run.
Decisions: Task Scheduler owns foreground `runtime serve`; Codex host owns stdio MCP.
Risks: Serena symbol extraction unavailable for the source registration; Spark quota unavailable.
Next steps: implement lifecycle commands and documentation.
Handoff: architecture to implementation.

## 2026-08-29 15:28 - implementer

Task: Implement and install Runtime autostart plus Codex MCP registration management.
Files changed: `tools/pf_runtime/windows_autostart.py`, `tools/pf_runtime/codex_mcp.py`, `tools/processforge.py`, `tools/smoke_runtime_mcp_autostart.py`.
Artifacts changed: implementation report.
Templates used: assignment capsule.
Tools used: PF CLI, Task Scheduler, Codex MCP CLI, Python smoke tests.
Decisions: dry-run by default; explicit apply/replace/force; deterministic per-workplace task.
Risks: installed 1.1.0 status probe remains degraded by timeout.
Next steps: documentation remediation and independent assurance.
Handoff: implementation to docs and review.

## 2026-08-29 15:41 - docs-maintainer

Task: Reconcile EN/RU Runtime, MCP, hooks, installation, indexes and limitations documentation.
Files changed: Runtime/MCP documentation set under `docs/`.
Artifacts changed: documentation remediation and final-fix reports.
Templates used: assignment capsule.
Tools used: PF worker-run, local Markdown link checker, stale-claim scan.
Decisions: distinguish required file-first runtime, optional long-lived Runtime, and host-owned MCP.
Risks: two broken RU links were found and fixed in follow-up tasks.
Next steps: independent assurance.
Handoff: docs to reviewer.

## 2026-08-29 15:57 - code-reviewer and implementer

Task: Review and remediate Runtime/MCP autostart candidate.
Files changed: `tools/pf_runtime/codex_mcp.py`, smoke and EN/RU autostart docs.
Artifacts changed: assurance review and remediation report.
Templates used: assurance assignment capsule.
Tools used: PF codex-exec worker, mocked drift repro, targeted smoke, release-test.
Decisions: default mode accepts compatible Python launchers; explicit `--python` is an exact pin.
Risks: worker assurance could not write to system temp; main run repeated the smoke successfully. `worker-run collect` failed on transcript cardinality although the review artifact was written.
Next steps: persist machine evidence and close the run.
Handoff: assurance to release-delivery.

## 2026-08-29 15:58 - release-manager

Task: Verify real machine state and record acceptance.
Files changed: none outside PF delivery artifacts.
Artifacts changed: machine acceptance and assurance follow-up.
Templates used: PF release-delivery task.
Tools used: source PF CLI, installed PF CLI, Windows Task Scheduler, CIM process inspection, Codex MCP CLI.
Decisions: keep Runtime task installed and running; remove only detached orphan MCP; keep Codex registration.
Risks: installed distribution is 1.1.0; source commands are unreleased; full reboot was not performed; two unrelated long-lived Runtime smoke failures remain.
Next steps: final follow-up review, run doctor and completion.
Handoff: release manager to project owner.
