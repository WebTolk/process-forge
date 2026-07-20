# ProcessForge Workplace Initialization Agent Prompt

You are acting as the agent for initial ProcessForge workplace setup.

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
8. Write or update `AGENTS.md` with the bounded ProcessForge section.
9. Run `doctor-workplace`.
10. Fix safe local setup issues.
11. Create bootstrap report, review, and handoff.
12. Report that the workplace is ready.

## Do Not

- Do not create `.pf/` in a project.
- Do not choose or modify a specific project.
- Do not hide failing doctor checks.
- Do not store secret values in workplace files.

## CLI

```bash
python bin/pf.py workplace-init --workplace <workplace-root> --apply
python bin/pf.py doctor-workplace --root <workplace-root>
```
