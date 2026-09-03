# mcp-patterns-for-processforge

Source: accepted `project-initialization-contract.md`.

- Ledger-first authorization binds every session operation to one project.
- Snapshot-authorized resolution permits only current, selected local resources.
- Runtime/MCP stays transport-thin; Core owns business logic and durable state.
- FTS5 and projections are rebuildable derived caches, not authorities.
- Registry configured, snapshot active, client visible and Ledger verified are separate states.
- Responses use stable fail-closed error codes and bounded navigation data, not raw diagnostics or dumps.
- Mutations are proposal/dry-run first and require explicit apply.
- Public artifacts expose refs and checksums; a session-authorized runtime result may expose the canonical path needed for local navigation.
