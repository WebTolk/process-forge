# ProcessForge Quickstart Prompts

This quickstart is for people. Copy one prompt into your AI agent. The agent
should use the complete command runbook in
[docs/getting-started/agent-prompts.md](docs/getting-started/agent-prompts.md).

## 1. Prepare The Tool

```text
Prepare ProcessForge on this machine. It is located at <processforge-root>.

Inspect the README and use docs/getting-started/agent-prompts.md as the
operational command runbook.

Verify that the distribution root is usable and tell me the exact path I should
use as <processforge-root>.
```

## 2. Set Up A Workplace By Guided Dialogue

```text
Initialize ProcessForge in step-by-step mode. It is located at
<processforge-root>.

Use explicit paths for the ProcessForge distribution, workplace, optional
global agent root, and project roots. Do not treat the current working directory
as a project unless I explicitly select it for project onboarding.
```

The guided setup command family is `workplace-setup start`,
`workplace-setup review`, `workplace-setup apply`, and
`workplace-setup status`.

## 3. Fully Automatic Setup

```text
Initialize ProcessForge in fully automatic mode. It is located at
<processforge-root>. First inspect the current AGENTS.md and setup skills.

Use explicit paths for the ProcessForge distribution, workplace, optional
global agent root, and project roots. Do not treat the current working directory
as a project unless I explicitly select it for project onboarding.
```

In automatic mode, the agent first explains what is where and what role it has,
proposes a setup scenario, gets approval, and only then applies changes.
Agent configuration folders such as `.codex`, `.claude`, `.agents`, or custom
names may become instruction or knowledge sources; they are not projects by
name or by launch location.

## 4. Create Shared Resources

```text
Create shared ProcessForge resources for this workplace.

Ask which resources are needed: knowledge packages, reusable templates, tools,
MCP providers, platform contracts, or all of them.

Work dependency-first. Register tools and MCP providers, create or import
knowledge packages, create reusable templates, then create platform contracts
that compose those resources for a concrete project context.
```

## 5. Onboard A Project

```text
Onboard this repository into ProcessForge.

Inspect the repository first, choose a conservative project type, connect it to
the existing workplace, and first verify that required workplace resources are
already present or explicitly out of scope.

Create the project-local .pf layer, read the generated .pf/START_AGENT_HERE.md,
run doctor-project, refresh the project context, and summarize what ProcessForge
now knows about the project. Run project-context-check and confirm whether the
snapshot is fresh, fresh_with_updates, stale, or broken.
```

## 6. Compose A Platform Stack

```text
Compose a project platform stack in ProcessForge.

Use platform contracts as composition manifests. If the stack has a parent and
child platform, model the parent/child relationship in extends or
requires.platforms. Connect knowledge packages, templates, tools, MCP providers,
capabilities, processes, coding standards, and project type hints by id. Run the
platform doctor and then refresh the project context snapshot.
```

## 7. Start A Run

```text
Create a ProcessForge run for my current request.

Use the default single-agent session model: one operator, one primary agent
session, one project, and one active process/run. Start the session with
session-start or agent-checkin, execute the process sequentially, use CLI
checks and gates for inspection, and check out before ending. Do not assume an
Agent Director or Supervisor is present unless the process explicitly uses
multi-agent, handoff, or external runtime-worker mechanics.

If the workplace supports Director, check the project effective mode before
using Director mechanics:

```bash
python bin/pf.py project-mode status --project-root <project-root> --workplace <workplace-root>
python bin/pf.py project-mode set --project-root <project-root> --mode simple
python bin/pf.py project-mode set --project-root <project-root> --mode organized --init-office
```

Use task-batch execution. Split the work into tasks, record iterations as work
progresses, write artifacts/reviews/handoffs when the process calls for them,
and close with run-summary and run-doctor.
```

## 8. Create A Custom Process

```text
Author a new ProcessForge process.

Use the process authoring flow rather than writing YAML by hand first. Ask me
for the process purpose, stages, roles, gates, artifacts, required knowledge,
and expected task loop. Review the draft, apply it, and verify the resulting
process.
```

## 9. Use Subagents

```text
Plan a ProcessForge-assisted multi-agent run.

Use the built-in multi-agent orchestration flow. Create and validate an
orchestrator task plan, apply it to create worker assignments and capsules,
launch each worker with only its worker launch prompt, and reconcile outputs
into an integration report before delivery.
```

## 10. Use Agent Ledger And Process Handoffs

```text
Plan a ProcessForge handoff with agent attendance tracking.

Register the relevant workplace agents, check in the active agent roles, create
or validate .pf/process-routes.yaml, create a handoff package, run
agent-director-tick to grant leases when the required role is online, and return
only concrete expected artifacts.
```

## 11. Validate Before Delivery

```text
Validate the repository before delivery.

Use the ProcessForge release and validation runbook for agents. Run the required
checks, rebuild the release archive with a neutral filename, test the archive,
and report exact pass/fail evidence before commit or push.
```

## 12. Run A Supervised Worker Smoke

```text
Use ProcessForge runtime drivers for a bounded supervised test run.

List and validate the built-in neutral runtime drivers, create or use an
orchestrator plan with runtime.default_driver set to test-echo-worker, run the
Process Execution Inspector for a small fixed number of ticks, and report the
worker-run status files and produced reports. The compatible technical commands
are `supervisor tick` and `supervisor run`; the clearer aliases are
`execution-inspector-tick` and `execution-inspector-run`.
```

## Required Order

1. Install ProcessForge distribution.
2. Verify ProcessForge itself.
3. Run guided workplace setup by default for human-led setup, or direct
   workplace-init only for explicit automatic setup.
4. Configure path constants and roots.
5. Configure knowledge roots.
6. Register tools and MCP servers.
7. Create or import knowledge packages.
8. Create reusable templates.
9. Create platform contracts.
10. Onboard project.
11. Create run/task workflow.
12. Create custom processes as needed.
13. Configure update sites when packages, tools, or workplace resources should
    receive operator-controlled updates.

Capabilities say what work may be needed, knowledge packages say where to read
the rules, and platform contracts compose application or domain stacks for
projects. Base technologies are knowledge packages and capabilities, not
platform contracts.

ProcessForge core is domain-agnostic. Platforms, inheritance, package
dependencies, and detection rules come from manifests and policy data.

For update checks, start with `python bin/pf.py update candidates refresh
--workplace <workplace>` and continue through `stage`, `verify`, `apply
--confirm`, or `rollback` as documented in
`docs/getting-started/update-system.md`.

Do not copy the whole ProcessForge repository into `.codex`, `.claude`,
`.agents`, or similar agent configuration folders. Install ProcessForge once as
a tool and tell the agent where it is installed; project-specific instructions
live in `.pf/START_AGENT_HERE.md`.
