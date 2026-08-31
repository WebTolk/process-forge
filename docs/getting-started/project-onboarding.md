# Project Onboarding

Project onboarding is run once per project after a workplace exists and after
required workplace resources are created, registered, validated, or explicitly
out of scope.

The project root must be selected explicitly. During machine or workplace setup,
do not treat the current working directory, the ProcessForge distribution root,
or a global agent configuration folder as the project unless the operator
confirms that exact directory as the project target.

It creates the project-local `.pf/` flow root:

- `.pf/AGENTS.md`
- `.pf/START_AGENT_HERE.md`
- `.pf/process-forge.yaml`
- `.pf/process-forge.local.yaml`
- `.pf/hooks.yaml`
- `.pf/assignments/first-assignment.yaml`
- `.pf/runtime/bin/pf.py`
- `.pf/contexts/project-context.snapshot.yaml`
- `.pf/contexts/project-context.snapshots/<snapshot-id>.yaml`
- `.pf/artifacts/project-onboarding-report.md`
- `.pf/reviews/project-onboarding-review.md`
- `.pf/handoffs/project-ready-handoff.md`

Command:

For dry-run, create or select `./my-project` first. Apply mode can create a
missing greenfield project root.

```bash
python bin/pf.py project-onboard --project-root ./my-project --workplace ./pf-workplace --type generic-software-project --apply
python bin/pf.py agent-start-prompt --project-root ./my-project
```

The public manifest declares `context_requirements` and `context_policy`.
`project-context-refresh` resolves them into a generated snapshot lock. Existing
assignment capsules stay pinned to the snapshot id and checksum they were
created with.

Project coordination mode is independent from workplace capability:

```bash
python bin/pf.py project-onboard --project-root ./my-project --workplace ./pf-workplace --type generic-software-project --coordination-mode inherit --apply
python bin/pf.py project-mode status --project-root ./my-project --workplace ./pf-workplace --json
python bin/pf.py project-mode set --project-root ./my-project --mode simple
python bin/pf.py project-mode set --project-root ./my-project --mode organized --init-office
```

Use `simple` for the default 1-1-1-1 flow. Use `organized` only when the
project should submit to the workplace Director Office or participate in
Director-managed cases, leases, handoffs, or error routes.

This process does not recreate the workplace, does not create missing shared
resources as a substitute for workplace setup, and does not copy global packages
into the project.

The project-local launcher reads private `.pf/process-forge.local.yaml` or `PROCESSFORGE_HOME` to find the ProcessForge distribution. Public files such as `.pf/START_AGENT_HERE.md` do not reveal the resolved distribution path.

Generic onboarding does not install host-specific Codex hooks and does not
require Runtime, MCP, or a Ledger session. Inside the linked project, the agent
follows `.pf/START_AGENT_HERE.md`: `pf.context`, conditional `pf.search`,
`pf.resolve`, then `pf.work.start` for substantive work.

Operator diagnostics remain available when needed:

```bash
pf doctor-project --project-root .
python .pf/runtime/bin/pf.py doctor-project --project-root .
```
