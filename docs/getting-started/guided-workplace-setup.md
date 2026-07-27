# Guided Workplace Setup

Guided workplace setup is the agent-first setup flow for a new machine. The agent asks questions in blocks, updates `answers.yaml`, creates a proposal before apply, applies the workplace through existing initialization mechanics, runs `doctor-workplace`, and writes project onboarding next steps.

The CLI supports the dialogue artifacts; it is not a terminal-only wizard.

## Commands

```bash
python bin/pf.py workplace-setup start --workplace <workplace-root> --session-id first-machine --apply
python bin/pf.py workplace-setup review --workplace <workplace-root> --session-id first-machine
python bin/pf.py workplace-setup apply --workplace <workplace-root> --session-id first-machine --apply
python bin/pf.py workplace-setup status --workplace <workplace-root> --session-id first-machine
```

Session files are written under:

```text
<workplace-root>/.pf-workplace/setup-sessions/<session-id>/
```

Expected artifacts:

- `answers.yaml`
- `proposal.yaml`
- `proposal.md`
- `review.md`
- `apply-report.md`
- `agent-instructions.md`
- `next-steps.md`

## Dialogue Blocks

Ask one block at a time:

1. Machine layout: ProcessForge root, workplace path, local docs path, project roots.
2. Agent environment: agent tools, instruction targets, global AGENTS policy.
3. Privacy and safety: local paths, public `path_ref`, secrets, update trust.
4. Resources: knowledge roots, package roots, tools, MCP servers, templates.
5. Platform contracts: neutral by default, real platforms only when explicitly defined.
6. Coordination: Director capability, default project mode, and whether to initialize Director Office now.
7. First project: optional immediate project onboarding plan, including project coordination mode.

## Agent Snippet

The apply step writes a short snippet:

```text
ProcessForge is installed at <processforge-root>.
Workplace is <workplace-root>.

Do not copy ProcessForge into agent config folders or projects.

Inside onboarded projects:
1. Read .pf/START_AGENT_HERE.md first.
2. Use python .pf/runtime/bin/pf.py from the project root.

Outside projects:
use python <processforge-root>/bin/pf.py.
```
