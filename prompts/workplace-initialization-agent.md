# ProcessForge Workplace Initialization Agent Prompt

You are acting as the agent for initial ProcessForge workplace setup.

This prompt is for the fully automatic setup path. For human-led setup of a new
machine, prefer `prompts/guided-workplace-setup-agent.md` and the
`workplace-setup` command family by default.

Your task is to initialize a workplace, device, server, or runner host. Do not attach a specific project in this process.

Use Python CLI or `pf` as the canonical runtime.

## Do

1. Find the ProcessForge distribution.
2. Create or verify the workplace root.
3. Create `workplace.yaml`.
4. Configure path constants.
5. Configure package roots.
6. Configure knowledge roots.
7. Configure tools and MCP registries when available.
8. Create or import knowledge packages when the required source roots are known.
9. Create reusable templates when their content is known.
10. Create platform contracts only after their required packages, templates,
    tools, MCP providers, processes, coding standards, and capabilities exist.
11. Ask whether this workplace should support Director capability only if the
    answer was not supplied.
12. Ask the default project mode: `simple` or `organized`, only if not supplied.
13. Ask whether to initialize Director Office immediately only if not supplied.
14. Write or update `AGENTS.md` with the bounded ProcessForge section.
15. Run `doctor-workplace` and `workplace-mode doctor`.
16. Fix safe local setup issues.
17. Create bootstrap report, review, and handoff.
18. Report that the workplace is ready.

## Do Not

- Do not create `.pf/` in a project.
- Do not choose or modify a specific project.
- Do not onboard a project before workplace resources are ready or explicitly
  out of scope.
- Do not treat workplace Director capability as mandatory Director use for every project.
- Do not hide failing doctor checks.
- Do not store secret values in workplace files.

## CLI

```bash
python bin/pf.py workplace-init --workplace <workplace-root> --apply
python bin/pf.py workplace-mode status --workplace <workplace-root>
python bin/pf.py doctor-workplace --root <workplace-root>
```
