# ProcessForge Project Onboarding Agent Prompt

You are acting as the agent that attaches a concrete project to an existing ProcessForge workplace.

Your task is to create `.pf/` in the project and prepare it for assignment-based work. Do not recreate the workplace.

Use `python bin/pf.py` from the ProcessForge distribution root, or `pf` /
`python .pf/runtime/bin/pf.py` inside an onboarded project. A normal linked
project does not contain ProcessForge core or `tools/processforge.py`.

Project onboarding is the third layer. It must happen after the workplace exists
and after required workplace resources are created, registered, validated, or
explicitly out of scope.

## Do

1. Find the project root.
2. Find the existing workplace root or `workplace.yaml`.
3. Verify that the workplace exists.
4. Verify that required workplace resources are present, validated, or explicitly out of scope.
5. Determine or accept the project type.
6. Determine project coordination mode: `inherit`, `simple`, or `organized`.
7. Capture `context_requirements` and `context_policy` in `.pf/process-forge.yaml`.
8. Create `.pf/`.
9. Create `.pf/process-forge.yaml`.
10. Create `.pf/process-forge.local.yaml`.
11. Create `.pf/AGENTS.md`.
12. Create `.pf/hooks.yaml`.
13. Resolve platform contracts.
14. Refresh project context snapshot; this writes `.pf/contexts/project-context.snapshot.yaml` and a generation under `.pf/contexts/project-context.snapshots/`.
15. Run `project-context-check --session-start --json` and record the status.
16. Create `.pf/assignments/first-assignment.yaml`.
17. Create an assignment capsule; it must pin the current snapshot id/checksum and must not use `latest`.
18. Generate `.pf/START_AGENT_HERE.md`.
19. Create `.pf/runtime/bin/pf.py`.
20. Check `project-mode status`.
21. Run `doctor-project` through `pf` or `.pf/runtime/bin/pf.py`.
22. Fix safe local issues.
23. Create onboarding report, review, and handoff.

## Do Not

- Do not recreate the workplace.
- Do not create missing shared resources inside project onboarding unless the
  operator explicitly expands scope to workplace resource authoring first.
- Do not write absolute local paths into public project files.
- Do not copy global packages into the project.
- Do not rewrite existing capsules when refreshing project context.
- Do not put `latest` resource references into capsules.
- Do not overwrite brownfield files without explicit force.
- Do not require Director Office for a project with effective `simple` mode.
- Do not set `organized` unless workplace Director capability exists or the operator explicitly enables it.

## CLI

```bash
python bin/pf.py project-onboard --project-root <project-root> --workplace <workplace-root> --type <project-type> --coordination-mode inherit --apply
python bin/pf.py project-context-check --project-root <project-root> --workplace <workplace-root> --session-start --json
python bin/pf.py project-mode status --project-root <project-root> --workplace <workplace-root>
python bin/pf.py agent-start-prompt --project-root <project-root>
```

Inside the onboarded project:

```bash
pf doctor-project --project-root .
pf project-context-check --project-root . --session-start --json
python .pf/runtime/bin/pf.py doctor-project --project-root .
```
