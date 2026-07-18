# ProcessForge Quickstart Prompts

This quickstart is for people. Copy one prompt into your AI agent. The agent
should use the complete command runbook in
[docs/getting-started/agent-prompts.md](docs/getting-started/agent-prompts.md).

## 1. Prepare The Tool

```text
Prepare ProcessForge on this machine.

Find the ProcessForge checkout or unpacked distribution, inspect the
documentation, and use docs/getting-started/agent-prompts.md as the operational
command runbook.

Verify that the distribution root is usable and tell me the exact path I should
use as <processforge-root>.
```

## 2. Initialize A Workplace

```text
Initialize a ProcessForge workplace.

Use the ProcessForge command runbook for agents. Create the workplace at the path
I provide or propose a clear local path. Run doctor-workplace, fix any structural
problems you can safely fix, and report the result.
```

## 3. Onboard A Project

```text
Onboard this repository into ProcessForge.

Inspect the repository first, choose a conservative project type, connect it to
the existing workplace, read the generated .pf/START_AGENT_HERE.md, run
doctor-project, and summarize what ProcessForge now knows about the project.
```

## 4. Start A Run

```text
Create a ProcessForge run for my current request.

Use task-batch execution. Split the work into tasks, record iterations as work
progresses, write artifacts/reviews/handoffs when the process calls for them,
and close with run-summary and run-doctor.
```

## 5. Create A Custom Process

```text
Author a new ProcessForge process.

Use the process authoring flow rather than writing YAML by hand first. Ask me
for the process purpose, stages, roles, gates, artifacts, required knowledge, and
expected task loop. Review the draft, apply it, and verify the resulting process.
```

## 6. Create Shared Resources

```text
Create shared ProcessForge resources for this project.

Ask whether the project needs reusable templates, knowledge packages, platform
contracts, or all of them. Keep shared resources in the workplace, reference
them by id, and run the matching doctor checks.
```

## 7. Use Subagents

```text
Plan a ProcessForge-assisted multi-agent run.

Keep tightly coupled work in the main agent. Use subagents only for independent
scopes, give each subagent a non-overlapping remit, require file-based evidence,
and reconcile their outputs into the current run before final delivery.
```

## 8. Validate Before Delivery

```text
Validate the repository before delivery.

Use the ProcessForge release and validation runbook for agents. Run the required
checks, rebuild the release archive with a neutral filename, test the archive,
and report exact pass/fail evidence before commit or push.
```
