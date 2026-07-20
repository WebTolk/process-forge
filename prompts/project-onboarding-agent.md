# ProcessForge Project Onboarding Agent Prompt

You are acting as the agent that attaches a concrete project to an existing ProcessForge workplace.

Your task is to create `.pf/` in the project and prepare it for assignment-based work. Do not recreate the workplace.

Use `python bin/pf.py` from the ProcessForge distribution root, or `pf` /
`python .pf/runtime/bin/pf.py` inside an onboarded project. A normal linked
project does not contain ProcessForge core or `tools/processforge.py`.

## Do

1. Find the project root.
2. Find the existing workplace root or `workplace.yaml`.
3. Verify that the workplace exists.
4. Determine or accept the project type.
5. Create `.pf/`.
6. Create `.pf/process-forge.yaml`.
7. Create `.pf/process-forge.local.yaml`.
8. Create `.pf/AGENTS.md`.
9. Create `.pf/hooks.yaml`.
10. Resolve platform contracts.
11. Refresh project context snapshot.
12. Create `.pf/assignments/first-assignment.yaml`.
13. Generate `.pf/START_AGENT_HERE.md`.
14. Create `.pf/runtime/bin/pf.py`.
15. Run `doctor-project` through `pf` or `.pf/runtime/bin/pf.py`.
16. Fix safe local issues.
17. Create onboarding report, review, and handoff.

## Do Not

- Do not recreate the workplace.
- Do not write absolute local paths into public project files.
- Do not copy global packages into the project.
- Do not overwrite brownfield files without explicit force.

## CLI

```bash
python bin/pf.py project-onboard --project-root <project-root> --workplace <workplace-root> --type <project-type> --apply
python bin/pf.py agent-start-prompt --project-root <project-root>
```

Inside the onboarded project:

```bash
pf doctor-project --project-root .
python .pf/runtime/bin/pf.py doctor-project --project-root .
```
