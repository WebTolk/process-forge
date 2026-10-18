# Evolution: evolve-20261002-02

Captured learning:
- MCP `pf.work.start` can accept typed scope intent without routing through the
  CLI adapter by validating with shared Core semantics and calling
  `ProcessExecutionService.start(..., scope_intent=...)`.
- Transport schemas must stay bounded: the MCP schema rejects unknown top-level
  and nested `scope_intent` fields before Core creates Work.
- Scope ownership matters: this task preserved the active owner of
  `tools/processforge.py` by implementing parity entirely inside the MCP server
  and smokes.

Rules or knowledge updates:
- No reusable global rule or memory update was requested.
- Python documentation was available through the Work resource layer as
  metadata-only context; implementation relied on existing local Core behavior
  and focused smoke coverage.

Deferred items:
- Commit and push.
- Full release/archive qualification.
- Installed Core update.
- Connected host proof.
