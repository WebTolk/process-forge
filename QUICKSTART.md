# ProcessForge Quickstart Prompts

This quickstart is for people. Copy one prompt into your AI agent. The agent
should use the complete command runbook in
[docs/getting-started/agent-prompts.md](docs/getting-started/agent-prompts.md).

## 1. Prepare The Tool

```text
Prepare ProcessForge on this machine.

Find the ProcessForge checkout or unpacked distribution, inspect the README,
and use docs/getting-started/agent-prompts.md as the operational command
runbook.

Verify that the distribution root is usable and tell me the exact path I should
use as <processforge-root>.
```

## 2. Initialize A Workplace

```text
Initialize a ProcessForge workplace.

Use the ProcessForge command runbook for agents. Create the workplace at the path
I provide or propose a clear local path. Run doctor-workplace, fix any structural
problems you can safely fix, and report the result.

Configure path constants, package roots, knowledge roots, tool registries, and
MCP registries before creating knowledge packages or platform contracts.
```

## 3. Create Shared Resources

```text
Create shared ProcessForge resources for this workplace.

Ask which resources are needed: knowledge packages, reusable templates, tools,
MCP providers, platform contracts, or all of them.

Work dependency-first. Register tools and MCP providers, create or import
knowledge packages, create reusable templates, then create platform contracts
that compose those resources for a concrete project context.
```

## 4. Onboard A Project

```text
Onboard this repository into ProcessForge.

Inspect the repository first, choose a conservative project type, connect it to
the existing workplace, read the generated .pf/START_AGENT_HERE.md, run
doctor-project, refresh the project context, and summarize what ProcessForge now
knows about the project.
```

## 5. Compose A Platform Stack

```text
Compose a project platform stack in ProcessForge.

Use platform contracts as composition manifests. If the stack has a parent and
child platform, model the parent/child relationship in extends or
requires.platforms. Connect knowledge packages, templates, tools, MCP providers,
capabilities, processes, coding standards, and project type hints by id. Run the
platform doctor and then refresh the project context snapshot.
```

## 6. Start A Run

```text
Create a ProcessForge run for my current request.

Use task-batch execution. Split the work into tasks, record iterations as work
progresses, write artifacts/reviews/handoffs when the process calls for them,
and close with run-summary and run-doctor.
```

## 7. Create A Custom Process

```text
Author a new ProcessForge process.

Use the process authoring flow rather than writing YAML by hand first. Ask me
for the process purpose, stages, roles, gates, artifacts, required knowledge,
and expected task loop. Review the draft, apply it, and verify the resulting
process.
```

## 8. Use Subagents

```text
Plan a ProcessForge-assisted multi-agent run.

Keep tightly coupled work in the main agent. Use subagents only for independent
scopes, give each subagent a non-overlapping remit, require file-based evidence,
and reconcile their outputs into the current run before final delivery.
```

## 9. Validate Before Delivery

```text
Validate the repository before delivery.

Use the ProcessForge release and validation runbook for agents. Run the required
checks, rebuild the release archive with a neutral filename, test the archive,
and report exact pass/fail evidence before commit or push.
```

## Required Order

1. Install ProcessForge distribution.
2. Verify ProcessForge itself.
3. Initialize workplace.
4. Configure path constants and roots.
5. Configure knowledge roots.
6. Register tools and MCP servers.
7. Create or import knowledge packages.
8. Create reusable templates.
9. Create platform contracts.
10. Onboard project.
11. Create run/task workflow.
12. Create custom processes as needed.

Capabilities say what work may be needed, knowledge packages say where to read
the rules, and platform contracts compose application or domain stacks for
projects. Base technologies are knowledge packages and capabilities, not
platform contracts.

ProcessForge core is domain-agnostic. Platforms, inheritance, package
dependencies, and detection rules come from manifests and policy data.

Do not copy the whole ProcessForge repository into `.codex`, `.claude`,
`.agents`, or similar agent configuration folders. Install ProcessForge once as
a tool and tell the agent where it is installed; project-specific instructions
live in `.pf/START_AGENT_HERE.md`.
