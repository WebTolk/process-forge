# Context Reconciliation Design

Status: existing mechanism confirmed

Observed behavior:

- `project-context-check` reports stale reasons and a policy action.
- Stale due to changed workplace manifest/MCP/tool registries blocked capsule creation.
- `project-context-refresh` produced a fresh snapshot and ran bounded search
  maintenance for the known project.

Validated in this run:

- stale before baseline capsule: `workplace_manifest`, `workplace-mcp-registry-registries-mcp-yaml`;
- stale before acceptance capsule: `workplace-tool-registry-registries-tools-yaml`;
- both were resolved by explicit `project-context-refresh`.

Residual: automatic safe reconcile in MCP bootstrap was not implemented here.
