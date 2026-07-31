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

## 2026-07-31 14:33 - codex

Task:
Harden real ProcessForge operator friction from Joomla plugin automation report without rewriting working flows.
Files changed:
tools/processforge.py; tools/smoke_official_pack_classifier_data_driven.py; tools/smoke_doctor_project_capability_waiver.py; docs/concepts/project-classifiers.md; docs/concepts/capability-resolution.md; docs/validation/doctor-project.md; CHANGELOG.md; checksums/processforge.sha256; .pf/logs/agent-log.md.
Artifacts changed:
.pf/logs/agent-log.md.
Templates used:
None.
Tools used:
Serena search attempt, PowerShell targeted reads, rg, apply_patch, py_compile, focused smokes.
Decisions:
Kept Serena/MCP availability outside PF responsibility. Added a narrow registry lock and atomic write for `pack-activate`; added inactive official classifier suggestions without domain hardcode; added explicit capability waiver handling for `doctor-project` registry declaration gaps while preserving strict capability resolution.
Risks:
The capability waiver is a doctor-level diagnostic override only. It does not satisfy context capability resolution and should not replace registering reusable workplace providers.
Next steps:
Run schema/public/checksum/release checks and commit if green.
Handoff:
None.

## 2026-07-31 13:50 - codex

Task:
Document optional shell-agent model selection after initial implementation push.
Files changed:
README.md; README.ru.md; QUICKSTART.md; CHANGELOG.md; checksums/processforge.sha256; .pf/logs/agent-log.md.
Artifacts changed:
.pf/logs/agent-log.md.
Templates used:
None.
Tools used:
PowerShell, rg, apply_patch, checksum validator, release-check, git diff --check.
Decisions:
Added top-level documentation and changelog visibility for `orchestrator-shell-plan-apply --model <model>`. Kept the deeper EN/RU concept and getting-started docs from the implementation commit as the detailed behavior reference.
Risks:
`QUICKSTART.ru.md` displayed unstable mojibake context in PowerShell, so this second documentation pass did not edit that file; the RU top-level README and RU deep docs already mention the option.
Next steps:
Commit and push the documentation-only slice.
Handoff:
None.

## 2026-07-31 13:36 - codex

Task:
Final validation for optional shell-agent model selection.
Files changed:
No additional source changes except this validation log entry and checksum refresh.
Artifacts changed:
.pf/logs/agent-log.md; checksums/processforge.sha256; .pf/runtime/release-test/latest-report.md; .pf/runtime/release-test/latest-report.json.
Templates used:
Existing runtime driver manifests.
Tools used:
py_compile, shell-agent smokes, runtime-driver registry smoke, schema/public/checksum validators, release-check, release-test --public, git diff --check.
Decisions:
Kept `--model` optional: empty model leaves shell command argv unchanged, non-empty model is propagated through plan normalization, assignment/capsule metadata, worker command state, environment, and runtime-driver model args.
Risks:
`release-test --public` completed with RESULT: FAIL only because `smoke_release_manifest_provenance_contract` requires clean Git for release-pack and this task intentionally leaves uncommitted changes. The target shell-agent smoke and release-check passed.
Next steps:
Commit the validated slice, then rerun `release-test --public` from clean Git before release packaging.
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

## 2026-07-31 13:13 - codex

Task:
Add optional shell-agent model selection for multi-agent orchestrator apply.
Files changed:
tools/processforge.py; tools/test_agents/pf_shell_agent.py; tools/smoke_orchestrator_shell_agents_with_subagent_policy.py; schemas/runtime-driver.schema.json; schemas/orchestrator-shell-agent-plan.schema.json; templates/runtime-drivers/generic-shell.yaml; templates/runtime-drivers/test-shell-agent.yaml; docs/concepts/runtime-drivers.md; docs/concepts/shell-agent-subagent-policy.md; docs/getting-started/agent-ledger-process-transitions.md; docs/ru/concepts/runtime-drivers.md; docs/ru/concepts/shell-agent-subagent-policy.md; docs/ru/getting-started/agent-ledger-process-transitions.md; checksums/processforge.sha256; .pf/logs/agent-log.md.
Artifacts changed:
.pf/logs/agent-log.md.
Templates used:
Existing runtime driver manifests.
Tools used:
Serena search/read memory, PowerShell, apply_patch, py_compile, focused smoke tests, schema/public/checksum validators.
Decisions:
`orchestrator-shell-plan-apply --model <model>` records the model on all workers in the applied shell-agent plan. Runtime drivers receive it through `agent_model`, `PF_AGENT_MODEL`, `{agent_model}`, and conditional `command.model_args`; if no model is set, no `--model` args are appended.
Risks:
Full public release-test was not run in this slice; prior log notes it can be timeout-prone on this Windows machine.
Next steps:
Run the broader public release-test and rebuild the release archive before publishing a new package from this HEAD.
Handoff:
None.
