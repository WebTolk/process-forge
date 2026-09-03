# Garage/Forge Runtime Contract

Status: partial

Garage uses one PF Core without requiring a long-lived Runtime. In this slice,
project-local Codex hooks can deliver events to Runtime when it is available
and fall back to durable Host/Core ingestion when it is not.

Forge remains the organized mode where long-lived Runtime is required. This
slice did not change Forge Runtime lifecycle commands or autostart contracts.

Residual: MCP stdio startup still needs a bounded Garage bootstrap maintenance
pass before serving tools.
