# Agent Command Runbook And Prompts

This page is for AI agents. Human-facing quickstarts should link here instead
of duplicating command lists. Keep release numbers out of prose, examples,
archive names, and reports.

## Operating Rules

- Treat ProcessForge as an installed tool, not as content to copy into
  `.codex`, `.claude`, `.agents`, or similar agent configuration folders.
- From the ProcessForge distribution root, use `python bin/pf.py`.
- Inside an onboarded project, use `python .pf/runtime/bin/pf.py`.
- Read `.pf/START_AGENT_HERE.md` before project work.
- For new human-led machine setup, use guided workplace setup by default:
  `workplace-setup start`, `workplace-setup review`,
  `workplace-setup apply`, and `workplace-setup status`.
- Use the fully automatic path only when the operator explicitly asks for it
  and provides the required paths and setup choices.
- Keep initialization order strict: workplace first, workplace resources
  second, project onboarding third.
- Keep workplace resources at the workplace level and project execution records
  under the project-local `.pf/` folder.
- Keep process definitions platform-agnostic. A process describes mechanics:
  stages, roles, gates, artifacts, capabilities, tools, hooks, and task loops.
- Treat platform contracts as workplace composition manifests. They compose
  knowledge packages, templates, tools, MCP providers, capabilities, processes,
  coding standards, project type hints, policies, and optional parent/child
  platform inheritance.
- Release-specific archive names belong in release checklists. Reusable prompt
  examples should use neutral archive filenames.
- `--interactive` is accepted by first-run initialization commands for UX
  compatibility; current commands remain file-first and do not require terminal
  prompting.
- For ordinary project work, start from the single-agent `1-1-1-1` model:
  one operator, one primary agent session, one project, and one active
  process/run. Check in with `session-start` or `agent-checkin`, run the
  process sequentially, use CLI checks and gates as inspection, and check out
  with `session-end` or `agent-checkout`.
- At session start, surface `project-context-check --session-start --json`.
  Continue on `fresh`, notify on `fresh_with_updates`, follow project policy on
  `stale`, and block on `broken`.
- Create assignment capsules from the current project context snapshot. Capsules
  pin snapshot id/checksum and must not use `latest` resource references.
- For `software-feature-development`, treat the process as a full software
  lifecycle: orchestration, intake, investigation, domain, architecture,
  implementation, assurance, release delivery, and evolve. Release/evolve may be
  `not_applicable`, but the decision must include reason and evidence.
- Do not treat package/build/install as a separate process. Use
  `execution_profile.delivery_profile` inside `software-feature-development`.
- Do not assume Agent Director, explicit leases, or Supervisor/Execution
  Inspector for simple work. Use them only when the selected process uses
  multi-agent coordination, process handoffs, or external runtime workers.
- For bounded worker orchestration, use `orchestrator-plan create`,
  `orchestrator-plan validate`, `orchestrator-plan apply`,
  `orchestrator-plan status`, and `worker-launch-prompt create`.
- Treat native subagents from the host AI environment as external executors:
  pass only ProcessForge assignment/capsule scope and expected report paths.
  Do not treat them as ProcessForge runtime drivers.

## Distribution Root Checks

```bash
python bin/pf.py version
python tools/validate-process-forge-schemas.py --root .
python tools/validate-public-cleanliness.py --root .
python tools/validate-process-forge-checksums.py --root . --check
python bin/pf.py release-test --root .
python bin/pf.py release-test --root . --public --fail-fast
python bin/pf.py release-pack --root . --output dist/processforge.zip
python bin/pf.py release-archive-test --archive dist/processforge.zip --root . --extracted-test full
git diff --check
```

## Default Guided Workplace Setup

Use this path for a new machine unless the operator explicitly asks for fully
automatic setup.

```bash
python <processforge-root>/bin/pf.py workplace-setup start --workplace <workplace-path> --session-id <session-id> --answers <answers-yaml> --apply
python <processforge-root>/bin/pf.py workplace-setup review --workplace <workplace-path> --session-id <session-id>
python <processforge-root>/bin/pf.py workplace-setup apply --workplace <workplace-path> --session-id <session-id> --apply
python <processforge-root>/bin/pf.py workplace-setup status --workplace <workplace-path> --session-id <session-id>
python <processforge-root>/bin/pf.py doctor-workplace --root <workplace-path>
```

During guided setup, ask questions in blocks, update `answers.yaml`, regenerate
the proposal, show `proposal.md` before apply, and do not onboard a project
until resource choices are settled.

## Fully Automatic Workplace Setup

Use this path only when required paths and choices are already known.

```bash
python <processforge-root>/bin/pf.py workplace-init --workplace <workplace-path> --apply
python <processforge-root>/bin/pf.py doctor-workplace --root <workplace-path>
```

## First Run Convenience

Use `first-run` only when workplace initialization and project onboarding should
run in sequence without guided dialogue. This is not the default human-led setup
path. Use it when the operator has provided `workplace`, `project-root`, and
`type`, and when shared resource authoring is already complete or explicitly out
of scope. For dry-run against a new project, create or select the target project
directory first.

```bash
python <processforge-root>/bin/pf.py first-run --workplace <workplace-path> --project-root <project-root> --type <project-type> --apply
```

## Project Onboarding

Project onboarding is allowed only after the workplace exists and required
shared resources are present, validated, or explicitly out of scope.

For dry-run, `<project-root>` must already exist. Apply mode can create a
missing greenfield project root.

```bash
python <processforge-root>/bin/pf.py project-onboard --project-root <project-root> --workplace <workplace-path> --type <project-type> --apply
python <processforge-root>/bin/pf.py agent-start-prompt --project-root <project-root>
```

After onboarding:

```bash
cd <project-root>
python .pf/runtime/bin/pf.py doctor-project --project-root .
python .pf/runtime/bin/pf.py project-context-refresh --project-root .
python .pf/runtime/bin/pf.py project-context-check --project-root .
```

## Process Authoring

```bash
python .pf/runtime/bin/pf.py process-authoring-start --project-root . --id <process-id> --title "<title>" --scope project --kind operational --apply
python .pf/runtime/bin/pf.py process-authoring-review --project-root . --id <process-id>
python .pf/runtime/bin/pf.py process-authoring-apply --project-root . --id <process-id> --apply
python .pf/runtime/bin/pf.py process-doctor --project-root . --process <process-id>
python .pf/runtime/bin/pf.py process-list --project-root .
python .pf/runtime/bin/pf.py process-describe --project-root . --process <process-id>
```

## Task Batch Run

```bash
python .pf/runtime/bin/pf.py session-start --project-root . --agent primary-agent --process task-batch-execution
python .pf/runtime/bin/pf.py run-create --project-root . --id <run-id> --title "<title>" --process task-batch-execution --apply
python .pf/runtime/bin/pf.py task-create --project-root . --run <run-id> --id <task-id> --title "<task title>" --process <process-id> --apply
python .pf/runtime/bin/pf.py iteration-add --project-root . --task <task-id> --kind work --summary "..." --apply
python .pf/runtime/bin/pf.py iteration-add --project-root . --task <task-id> --kind debug --summary "..." --apply
python .pf/runtime/bin/pf.py iteration-add --project-root . --task <task-id> --kind fix --summary "..." --apply
python .pf/runtime/bin/pf.py iteration-add --project-root . --task <task-id> --kind review --summary "..." --apply
python .pf/runtime/bin/pf.py task-complete --project-root . --task <task-id> --summary "..." --apply
python .pf/runtime/bin/pf.py run-summary --project-root . --run <run-id> --apply
python .pf/runtime/bin/pf.py run-doctor --project-root . --run <run-id>
python .pf/runtime/bin/pf.py session-end --project-root .
```

## Workplace Resource Authoring

Register tools and MCP providers:

```bash
python <processforge-root>/bin/pf.py tool-register --workplace <workplace-path> --id <tool-id> --capability <capability> --command "<command without secrets>" --apply
python <processforge-root>/bin/pf.py mcp-register --workplace <workplace-path> --id <mcp-id> --capability <capability> --command "<command without secrets>" --apply
```

Reusable template:

```bash
python <processforge-root>/bin/pf.py template-create --workplace <workplace-path> --id <template-id> --title "<title>" --apply
python <processforge-root>/bin/pf.py template-doctor --workplace <workplace-path> --template <template-id>
```

Knowledge package:

```bash
python <processforge-root>/bin/pf.py knowledge-package-create --workplace <workplace-path> --id <package-id> --title "<title>" --package-root global --apply
python <processforge-root>/bin/pf.py knowledge-package-doctor --workplace <workplace-path> --package <package-id>
```

Platform contract:

```bash
python <processforge-root>/bin/pf.py platform-create --workplace <workplace-path> --id <platform-id> --title "<title>" --apply
python <processforge-root>/bin/pf.py platform-contract-install --workplace <workplace-path> --id <platform-id> --required-packages <package-id> --required-tools <tool-id> --required-mcp <mcp-id> --required-templates <template-id> --apply
python <processforge-root>/bin/pf.py platform-contract-doctor --workplace <workplace-path> --platform <platform-id>
```

Knowledge resources:

```bash
python <processforge-root>/bin/pf.py knowledge-add-url --workplace <workplace-path> --package <package-id> --url <url> --apply
python <processforge-root>/bin/pf.py knowledge-add-resource --workplace <workplace-path> --package <package-id> --resource-file <resource-yaml> --apply
python <processforge-root>/bin/pf.py knowledge-index-refresh --workplace <workplace-path> --package <package-id> --apply
```

Platform contracts should be created after their required packages, templates,
tools, MCP providers, processes, coding standards, and capabilities exist.

## Human Prompt: Setup

```text
Set up ProcessForge for this machine in guided setup mode. Use the agent command
runbook in the repository documentation, ask setup questions in blocks, create
or verify the workplace, configure workplace resources before project onboarding,
run doctor checks, and report the exact paths and next onboarding step.
```

## Human Prompt: Fully Automatic Setup

```text
Set up ProcessForge automatically. Use the explicit paths and choices I provide,
skip guided dialogue unless a required answer is missing, initialize or verify
the workplace, configure/register shared resources, create platform contracts
after their dependencies, then onboard the project only if a project path is
provided. Run doctor checks and report assumptions and skipped areas.
```

## Human Prompt: Project Work

```text
Use ProcessForge for this task. Read .pf/START_AGENT_HERE.md first, create or
reuse a run, split the request into tasks, record iterations, keep artifacts in
.pf, run the relevant checks, and finish with a concise evidence-based handoff.
```

## Subagent Prompt: Documentation Specialist

```text
You are a ProcessForge documentation subagent.

Scope: documentation only. Do not edit source code, package manifests, release
artifacts, or generated checksums unless the main agent explicitly assigns them.

Tasks:
- read the relevant docs and assignment;
- update only the assigned documentation files;
- keep human docs prompt-only where requested;
- keep agent docs command-complete;
- avoid embedding release numbers in prose or archive examples;
- return a file list, summary, and residual risks.
```

## Subagent Prompt: Implementation Specialist

```text
You are a ProcessForge implementation subagent.

Scope: code or schema files explicitly assigned by the main agent. Do not write
to documentation files owned by another subagent.

Tasks:
- inspect the existing command and schema patterns before editing;
- make the smallest compatible change;
- run focused compile/schema checks if available;
- report exact commands, outputs, changed files, and follow-up risks.
```

## Subagent Prompt: Test And Release Specialist

```text
You are a ProcessForge test and release subagent.

Scope: validation only unless explicitly asked to repair a failing gate.

Tasks:
- run the requested validation commands;
- rebuild release archives only with neutral filenames for documentation-facing
  evidence;
- test the archive after packaging;
- report pass/fail status with command names and the first actionable failure.
```

## Subagent Prompt: Review Specialist

```text
You are a ProcessForge review subagent.

Scope: review changed files and evidence. Do not change files unless the main
agent asks for a repair.

Tasks:
- look for behavior regressions, stale commands, current-version references in
  documentation, misplaced human/agent instructions, and missing validation;
- cite files and lines for findings;
- separate blocking findings from non-blocking follow-up.
```
