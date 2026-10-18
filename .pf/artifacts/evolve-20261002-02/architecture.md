# evolve-20261002-02 Architecture Plan

Timestamp: 2026-10-02T13:07:20Z

Architecture:
- Add MCP-local `scope_intent_tool_schema()` in `tools/pf_runtime/mcp_server.py`.
- Keep the schema narrow and explicit, with `additionalProperties: false` at
  the scope object, predecessor object, assignment object, and nested report
  and ownership objects.
- Keep semantic validation in the existing shared function
  `creation_scope_intent`.
- For `pf.work.start`, route to `ProcessExecutionService.start` directly so the
  typed scope can be passed without editing the active-owner CLI adapter.

Implementation plan:
- Extend `pf.work.start` allowed arguments with `scope_intent`.
- Validate `scope_intent` only when supplied.
- Preserve objective-only start behavior.
- Extend MCP contract smoke to verify schema publication.
- Extend sessionless MCP work-start smoke to verify:
  - objective-only start still works,
  - typed scope creates a capsule with expected normalized scope,
  - invalid typed scope is rejected before Work publication.

Decision log:
- Do not edit `tools/processforge.py`; it is outside the current safe writer
  boundary.
- Do not add a new public helper module; the schema is MCP presentation detail.
- Do not accept a `scope_file` path through MCP; MCP receives typed JSON, while
  CLI remains path/file based.
