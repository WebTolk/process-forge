# Capability Single Truth Audit

Generated: 2026-08-24 12:00 +04

## Finding

The current project initialization status separates resource categories and
shows no required/recommended MCP providers for this project:

- `resources.mcp.required: 0`;
- `resources.mcp.recommended: 0`;
- `resources.mcp.activated: 0`;
- top-level `mcp: not_configured`.

This means Codex hook installation and MCP capability readiness are separate
truths. Installed project-local hooks do not prove MCP registration, and MCP
registry entries do not prove Codex has loaded them.

## Required Product Rule

Garage should expose a single diagnostic view that keeps the layers distinct:

1. project initialization artifacts;
2. Codex hook installation;
3. real Codex hook ingress;
4. Ledger-bound current session;
5. MCP registration and tool visibility;
6. local search readiness.

Status: `design_gap`.
