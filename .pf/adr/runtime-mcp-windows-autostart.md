# ADR: Windows Autostart Ownership For Runtime And MCP

Status: accepted
Date: 2026-08-29

## Context

ProcessForge has two different process lifecycles:

- PF Runtime is a workplace-scoped long-lived HTTP lifecycle host with a singleton lock, readiness endpoint, scheduler and durable operator state.
- The current PF MCP adapter is a stdio server. Its client must create the process and own the stdin/stdout pipes used for MCP JSON-RPC.

The existing `runtime start` command creates a detached process. It is suitable for an explicit interactive start, but a system scheduler cannot supervise that detached child. Starting `mcp_server.py` as an unrelated background process leaves it without an MCP client and is not a usable MCP registration.

## Decision

### Runtime

On Windows, ProcessForge supports opt-in per-user autostart through Windows Task Scheduler.

- The trigger is user logon, not machine boot. Workplace data, Python, repositories and agent credentials are user-scoped.
- Task Scheduler runs `runtime serve` in the foreground and therefore owns the process lifecycle.
- The task runs as the current interactive user with least privilege and no stored password.
- One deterministic task is created per workplace. Its name contains a short hash of the normalized workplace path, while the public documentation uses placeholders only.
- Multiple instances are ignored and the existing Runtime singleton remains the final safety boundary.
- The task has a short logon delay, unlimited execution time and bounded restart-on-failure settings.
- Install and remove are explicit `--apply` operations. Status is read-only and detects command, workplace or working-directory drift.
- The action points at the stable installed ProcessForge entrypoint. In-place core updates are picked up on the next Runtime restart. Moving Python or the installation requires reinstalling the task.

The supported CLI surface is:

```text
pf runtime autostart install --workplace <workplace> [--apply]
pf runtime autostart status --workplace <workplace>
pf runtime autostart remove --workplace <workplace> [--apply]
```

### MCP

The stdio MCP server is not registered with Windows Task Scheduler.

- The Codex host owns and starts the stdio process from its persistent MCP configuration.
- ProcessForge provides opt-in `status`, `install` and `remove` commands for the Codex MCP registration; it does not silently edit host configuration.
- A matching existing registration is idempotent. Replacing a foreign or drifted registration requires an explicit replacement option.
- Codex must be restarted or reloaded after a registration change. Each fresh host session starts its own connected Python MCP process.
- A future always-on MCP service would require a streamable HTTP transport, authentication and a separate protocol/security decision. It is not emulated by detaching the current stdio server.

The supported CLI surface is:

```text
pf codex-mcp status --workplace <workplace>
pf codex-mcp install --workplace <workplace> [--apply] [--replace]
pf codex-mcp remove --workplace <workplace> [--apply]
```

## Rejected Alternatives

- Startup-folder scripts: weak status/removal semantics and no restart policy.
- Scheduling `runtime start`: the scheduled action exits after detaching, so Task Scheduler cannot supervise Runtime.
- Windows Service: requires elevated installation and a service-account/access model that does not match the current user-scoped workplace.
- Scheduling `mcp_server.py`: creates an unconnected stdio process with no useful transport owner.
- Implementing streamable HTTP only to obtain autostart: materially expands protocol, authentication and exposure scope and is not required for local Codex clients.

## Consequences

- Runtime and MCP have different but explicit owners.
- Autostart remains opt-in and reversible.
- Runtime can start before Codex and collect hook/runtime traffic for all projects in the workplace.
- MCP starts only when a configured host needs it; no idle detached MCP process is required.
- Windows-specific behavior stays in an adapter module. PF Core and non-Windows file-first operation remain platform-neutral.
