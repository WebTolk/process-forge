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
8. Ask whether this workplace should support Director capability.
9. Ask the default project mode: `simple` or `organized`.
10. Ask whether to initialize Director Office immediately.
11. Write or update `AGENTS.md` with the bounded ProcessForge section.
12. Run `doctor-workplace` and `workplace-mode doctor`.
13. Fix safe local setup issues.
14. Create bootstrap report, review, and handoff.
15. Report that the workplace is ready.

## Do Not

- Do not create `.pf/` in a project.
- Do not choose or modify a specific project.
- Do not treat workplace Director capability as mandatory Director use for every project.
- Do not hide failing doctor checks.
- Do not store secret values in workplace files.

## CLI

```bash
python bin/pf.py workplace-init --workplace <workplace-root> --apply
python bin/pf.py workplace-mode status --workplace <workplace-root>
python bin/pf.py doctor-workplace --root <workplace-root>
```
