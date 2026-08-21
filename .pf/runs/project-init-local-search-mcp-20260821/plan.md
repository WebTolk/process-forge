# Plan: Project initialization and snapshot-bound local MCP search

1. Establish the governed scope, current context, and bounded independent inventories.
2. Audit current initialization, snapshot resolution, MCP routing, and resource representations.
3. Produce architecture and decision records before product-code changes.
4. Implement one Core initialization service plus a snapshot-bound SQLite FTS5 search service; keep CLI and MCP thin adapters.
5. Validate complete/interrupted initialization, search isolation, process guidance, regressions, reviews, and release gates.

Constraints: use `software-feature-development`; do not select the web-oriented backend specialization wholesale; SQLite FTS5 is the approved search technology; initialization writes require explicit `apply: true`.
