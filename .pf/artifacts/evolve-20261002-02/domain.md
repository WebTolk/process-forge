# evolve-20261002-02 Domain Modeling

Timestamp: 2026-10-02T13:06:30Z

Domain notes:
- A Work scope is immutable creation input. MCP may pass it only during
  `pf.work.start`; resume and transition paths must not widen an existing
  capsule.
- MCP receives a typed JSON object, while CLI receives equivalent JSON bytes
  through `--scope-file`.
- The shared source of truth for scope semantics is
  `creation_scope_intent`.
- MCP JSON Schema is an admission layer, not the final authority.

Domain model:
- `scope_intent.schema_version`: versioned local operator intent, currently `1`.
- `scope_intent.assignment`: bounded assignment fields only.
- `scope_intent.predecessor`: optional exact lineage selector.
- `scope_intent.predecessor_handoff`: optional `.pf/handoffs/` transfer record.
- `ProcessExecutionService.start(scope_intent=...)`: final creator of the
  assignment, run and immutable capsule.

Domain rules:
- Reject arbitrary top-level MCP arguments.
- Reject arbitrary assignment fields inside `scope_intent`.
- Reject invalid actions before Work publication.
- Preserve objective-only `pf.work.start` compatibility.
- Do not edit active owner scope for `tools/processforge.py`.
- Do not install, restart or reconnect infrastructure as part of this task.
