# AGENTS.md

## Mission

Use ProcessForge as a file-first process system. Work through assignments, execution contexts, artifacts, reviews, handoffs, logs, and ADRs.

## Boot Sequence

1. Read this file.
2. Read `.pf/process-forge.yaml`.
3. Call `pf.context` with the project root, or read the current snapshot only
   when MCP is unavailable.
4. Use `pf.search` for authorized project knowledge and `pf.resolve` before
   opening ProcessForge-managed resource roots.
5. Call `pf.work.start` with the objective when work becomes substantive.
6. Read the selected assignment and immutable Execution Context Package.
7. Check allowed and forbidden files before editing.
8. Execute the task and save durable outputs.
9. Update the assignment log and create the required review or handoff.

## Core Rules

- File-only mode is the default.
- One file scope has one responsible writer.
- Assignments define the work boundary.
- Do not edit files outside the assignment scope without a handoff.
- Approved artifacts are protected.
- Execution Context Packages are immutable snapshots.
- Process versions are immutable.
- Runner and backend support are optional future modes, not requirements.
- Public product files must not include private paths, secrets, machine names, or temporary private notes.
- Use stable machine-readable ids for statuses, processes, artifacts, assignments, templates, and packages.
- Create every repository-local temporary directory under `.pf/tmp/`; never create temporary worker, debug, staging, or scratch directories at the repository root.
- In particular, do not create root directories named `.pf-worker-shell-*` or similar runner sandboxes. Clean `.pf/tmp/` outputs after use unless they are declared durable evidence.
- System temporary directories are allowed only for isolated tests that never write a temporary directory into the repository.
- During ordinary project work, do not install, start, restart, or repair PF
  Runtime, MCP, host hooks, or Agent Ledger. Use available PF tools. If PF
  returns an operator-level infrastructure blocker, report it to the operator.
- Current `pf.context`/snapshot state outranks historical generated reports.
  Do not treat a report marked `stale` or `historical` as current truth.

## Standard Statuses

Artifact statuses:

```text
missing
draft
ready_for_review
approved
rejected
stale
superseded
archived
```

Review result statuses:

```text
pass
pass_with_conditions
warn
fail
skipped
```

Upgrade assessment results:

```text
safe
requires_approval
requires_migration
blocked
```

## Logging Format

Use append-only log entries:

```markdown
## YYYY-MM-DD HH:MM - <role>

Task:
Files changed:
Artifacts changed:
Templates used:
Tools used:
Decisions:
Risks:
Next steps:
Handoff:
```

## Handoff Format

```markdown
# Handoff: <from> -> <to>

Objective:
Current status:
Input artifacts:
Files changed:
Files not to touch:
Known issues:
Required checks:
Next recommended action:
```
