# Agent Log

## 2026-07-13 10:45 - Orchestrator

Task:
Create ProcessForge bootstrap as a file-first product.

Files changed:
See artifacts/changed-files.md.

Artifacts changed:
Bootstrap artifacts, ADRs, assignments, reviews, and handoffs.

Templates used:
ProcessForge bootstrap templates created during this run.

Tools used:
Serena, PhpStorm repository check, shell fallback for non-code file inventory, apply_patch.

Decisions:
Private research remains outside release inventory.

Risks:
The product needs deeper semantic validation after real project use.

Next steps:
Complete validation and public cleanliness review.

Handoff:
handoffs/orchestrator-to-next.md

## 2026-07-13 11:05 - Orchestrator

Task:
GitHub repository creation and push.

Files changed:
.gitignore, logs/task-log.md, logs/agent-log.md.

Artifacts changed:
Not applicable.

Templates used:
Not applicable.

Tools used:
gh, git.

Decisions:
Use `webtolk/process-forge` as the private GitHub repository target.

Risks:
No existing git history is available in this checkout.

Next steps:
Commit and push main branch.

Handoff:
Not applicable.

## 2026-07-26 01:50 - Codex

Task:
Implement Agent Ledger, Process Transitions, Agent Director, Continuation Capsule, and Orchestrator Shell Agents with Subagent Policy MVP.

Files changed:
tools/processforge.py; tools/test_agents/pf_shell_agent.py; tools/smoke_agent_ledger.py; tools/smoke_process_transition_handoff.py; tools/smoke_agent_director_tick.py; tools/smoke_orchestrator_shell_agents_with_subagent_policy.py; schemas/*agent* and handoff/route/continuation/orchestrator shell schemas; templates; processes; prompts; EN/RU docs; examples; checksum inventory; release archive.

Artifacts changed:
.pf/artifacts/agent-ledger-process-transitions-report.md; .pf/reviews/agent-ledger-process-transitions-review.md; .pf/handoffs/agent-ledger-process-transitions-handoff.md.

Templates used:
Project-local .pf workflow, existing runtime-driver/supervisor/orchestrator-plan templates, new ledger/route/handoff/continuation templates.

Tools used:
Serena attempted for symbol analysis; shell/ripgrep fallback used because Python symbols were unavailable; apply_patch; ProcessForge public smokes and release/archive checks.

Decisions:
Keep real external agent ecosystem drivers out of public core. Implement shell-agent subagent behavior through neutral simulated public reports. Preserve existing `orchestrator-plan apply` semantics and put auto-supervisor behavior only behind `orchestrator-shell-plan-apply`.

Risks:
Continuation resume is MVP partial and records readiness/resume state without launching a downstream process automatically.

Next steps:
Review diff and commit the completed MVP slice if accepted.

Handoff:
.pf/handoffs/agent-ledger-process-transitions-handoff.md
## 2026-07-31 09:42 - codex

Task:
Implement neutral cascade parameters for project context snapshots. Keep ProcessForge domain-neutral and do not parse AGENTS.md as a machine parameter source.
Files changed:
Planned: tools/processforge.py, schemas, templates, docs/concepts, smoke tests.
Artifacts changed:
Pending.
Templates used:
None.
Tools used:
Serena, PowerShell, apply_patch.
Decisions:
Parameter values start at workplace by default; organization and direction remain optional future layers; platform/toolchain may define resources or contracts but the resolver merges any structured parameters uniformly when present.
Risks:
Inline local credentials are allowed as ordinary private/local values, so public export boundaries need explicit checks.
Next steps:
Add resolver, schemas/templates/docs, smoke coverage, and run targeted checks.
Handoff:
None.

## 2026-07-31 10:42 - codex

Task:
Clarify ProcessForge setup documentation after local workplace diagnostics and document the neutral cascade parameter model.
Files changed:
README/QUICKSTART, agent prompts, getting-started setup/onboarding docs, workplace/project boundary docs, parameter/context concepts.
Artifacts changed:
.pf/logs/agent-log.md.
Templates used:
None.
Tools used:
Serena project activation, PowerShell, apply_patch.
Decisions:
Documented that current working directory and agent folder names do not assign ProcessForge roles; setup must use explicit distribution, workplace, agent-root, and project-root paths. Documented workplace-starting parameter resolution and project/assignment overrides.
Risks:
None identified before validation.
Next steps:
Run schema/public/checksum and focused parameter smoke checks, then commit and push.
Handoff:
None.

## 2026-07-31 10:48 - codex

Task:
Validation for cascade parameters and documentation boundary update.
Files changed:
No additional source changes except checksum refresh and this log entry.
Artifacts changed:
.pf/logs/agent-log.md; checksums/processforge.sha256.
Templates used:
None.
Tools used:
py_compile, parameter release-test smokes, schema validator, public-cleanliness validator, checksum validator, release-check, git diff --check.
Decisions:
Accepted focused parameter smoke coverage plus schema/public/checksum/release-check gates. Full public release-test was attempted but timed out in smoke_orchestrator_shell_agents_with_subagent_policy; related child processes were stopped and Serena processes were left running.
Risks:
Full public release-test remains timeout-prone on this Windows machine; no validation failures were observed before timeout, but the command did not produce a final pass report.
Next steps:
Commit and push the validated source/docs/checksum slice.
Handoff:
None.

## 2026-07-31 09:55 - codex

Task:
Completed neutral cascade parameters MVP for project context snapshots.
Files changed:
tools/processforge.py; schemas for manifests, workplace, process, assignment, capsule, snapshot, platform, specialization, init answers; templates; docs/concepts; new parameter smoke tests; checksum inventory.
Artifacts changed:
.pf/logs/agent-log.md.
Templates used:
None.
Tools used:
PowerShell, apply_patch, ProcessForge release-test, schema/public/checksum validators.
Decisions:
The resolver starts parameter values at workplace; AGENTS.md is not parsed; active platform/specialization/project/process/task sources can contribute structured parameters; maps merge recursively, scalar values replace, lists of objects merge by id, and lists without ids replace.
Risks:
Inline credentials are now possible in local/private parameter sources by design; public/export sanitization remains a separate policy concern.
Next steps:
If this slice is accepted, refresh any installed distribution copy and run the broader public release-test before packaging.
Handoff:
None.
