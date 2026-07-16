# Agent Prompts

ProcessForge ships two copy-paste prompts for first-run work:

- `prompts/workplace-initialization-agent.md`
- `prompts/project-onboarding-agent.md`

After onboarding a project, generate the project-specific start prompt:

```bash
python tools/processforge.py agent-start-prompt --project-root ./my-project
```

The command prints `.pf/START_AGENT_HERE.md` and creates it if it is missing.

The generated prompt uses:

```bash
pf doctor-project --project-root .
python .pf/runtime/bin/pf.py doctor-project --project-root .
```

It must not assume that `tools/processforge.py` exists in a normal linked project.
