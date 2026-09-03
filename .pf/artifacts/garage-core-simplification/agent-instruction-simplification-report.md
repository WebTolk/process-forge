# Agent Instruction Simplification Report

Date: 2026-08-24
Status: pass

`.pf/START_AGENT_HERE.md` now presents the Garage-first path:

1. read `.pf/AGENTS.md`;
2. call `pf.context` with `project_root`, or read the snapshot if MCP is unavailable;
3. use `pf.search` for snapshot-authorized knowledge, template, process, and tool metadata;
4. use `pf.resolve` before opening resource roots;
5. move into assignments and governed work only when the work is substantive.

The ordinary path no longer asks a fresh agent to dispatch hooks or wait for a
session before it can read project context.
