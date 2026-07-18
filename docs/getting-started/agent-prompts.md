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
- Keep workplace resources at the workplace level and project execution records
  under the project-local `.pf/` folder.
- For public examples and reports, use neutral release archive names such as
  `dist/processforge-release.zip`.

## Distribution Root Checks

```bash
python bin/pf.py version
python tools/validate-process-forge-schemas.py --root .
python tools/validate-public-cleanliness.py --root .
python tools/validate-process-forge-checksums.py --root . --check
python bin/pf.py release-test --root .
python bin/pf.py release-pack --root . --output dist/processforge-release.zip
python bin/pf.py release-archive-test --archive dist/processforge-release.zip
git diff --check
```

## Workplace Setup

```bash
python <processforge-root>/bin/pf.py workplace-init --workplace <workplace-path> --apply
python <processforge-root>/bin/pf.py doctor-workplace --root <workplace-path>
```

## Project Onboarding

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
python .pf/runtime/bin/pf.py run-create --project-root . --id <run-id> --title "<title>" --process task-batch-execution --apply
python .pf/runtime/bin/pf.py task-create --project-root . --run <run-id> --id <task-id> --title "<task title>" --process <process-id> --apply
python .pf/runtime/bin/pf.py iteration-add --project-root . --task <task-id> --kind work --summary "..." --apply
python .pf/runtime/bin/pf.py iteration-add --project-root . --task <task-id> --kind debug --summary "..." --apply
python .pf/runtime/bin/pf.py iteration-add --project-root . --task <task-id> --kind fix --summary "..." --apply
python .pf/runtime/bin/pf.py iteration-add --project-root . --task <task-id> --kind review --summary "..." --apply
python .pf/runtime/bin/pf.py task-complete --project-root . --task <task-id> --summary "..." --apply
python .pf/runtime/bin/pf.py run-summary --project-root . --run <run-id> --apply
python .pf/runtime/bin/pf.py run-doctor --project-root . --run <run-id>
```

## Workplace Resource Authoring

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
python <processforge-root>/bin/pf.py platform-contract-doctor --workplace <workplace-path> --platform <platform-id>
```

## Human Prompt: Setup

```text
Set up ProcessForge for this machine. Use the agent command runbook in the
repository documentation, create or verify the workplace, run doctor checks, and
report the exact paths and next onboarding step.
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
