<!-- PF:ENTRY:BEGIN contract=1.1.0 -->
## ProcessForge startup contract

This project is governed by ProcessForge (PF). This section is the startup
contract; `.pf/` holds state and further instructions. It grants no file,
tool, resource, process or infrastructure permissions by itself.

1. Locate this project's `.pf/process-forge.yaml` and read it. Call `pf.context`
   for this project root. If MCP is unavailable, use the existing project PF
   CLI and current `.pf/contexts/project-context.snapshot.yaml`; check freshness
   with `project-context-check`. Do not install or start tools to obtain context.
2. Before substantive work, require a valid, current context with no blocking
   readiness or policy result. Missing, stale, broken, conflicting or ambiguous
   context means stop the dependent work and report the exact blocker and
   required operator action. Historical reports do not override current state.
3. For continuation, discover candidates through `pf.continuation.status` or
   read the named continuation. Select exact run/assignment/context ids, create
   a continuation with explicit apply if needed, then `pf.continuation.resume`.
   Missing or ambiguous selection must not create Work. Without a bound session,
   pass returned selectors to every Work call. Use `pf.work.start` for new work.
   Follow PF's returned identity; never choose the first or newest assignment.
   If `process_choice_required`, select only an offered process and call again
   with `process_id`; do not infer a choice from a default among alternatives.
   If the objective cannot disambiguate the choice, ask the user.
4. Read `pf.work.state`, its selected assignment and immutable context capsule.
   Verify matching project/run/assignment/context identity, validity, current
   stage, allowed actions, read/write scope and obligations before acting.
   Empty grants grant nothing. A denied action or required unavailable resource
   blocks dependent work; do not broaden scope or rebuild the capsule yourself.
5. Use `pf.search`/`pf.resolve` for authorized project navigation. For Work
   resources use `pf.work.search`/`pf.work.resolve` with the exact returned run,
   assignment and context ids. Resolve before opening PF-managed resource roots;
   load only the authorized instructions, knowledge and templates needed now.
6. Satisfy the current stage, record artifacts/evidence and call
   `pf.work.transition` with outcome and evidence. The pinned process selects
   stages: never supply `next_stage` or edit lifecycle state manually. Repeat
   state/work/transition until PF returns `action: run_completed`. Use equivalent
   existing CLI operations when MCP is unavailable; do not invent commands.
7. Respect one writer per scope. Keep approved artifacts, process versions and
   capsules immutable. Use a governed handoff for scope/context changes. Keep
   repository scratch under `.pf/tmp/`; remove it unless retained as evidence.
   Never put private paths, credentials or machine details in public outputs.
8. Ordinary work must not install, start, restart or repair PF Runtime, MCP,
   host hooks or Agent Ledger. Report infrastructure blockers to the operator.
   File-only work does not require these services. Completion handoffs are
   advisory and do not authorize infrastructure or external-session actions.

Specialized work begins only after PF resolves its valid context and obligations.
This text defines conduct; technical access enforcement belongs to the host/PF.
<!-- PF:ENTRY:END -->

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
