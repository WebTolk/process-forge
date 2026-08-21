# workplace-mcp-surface-audit

Source: accepted `project-initialization-contract.md`.

The workplace model is registry-backed: an MCP record can be configured, activated through an explicit platform/specialization/override, present in a project snapshot, visible in a client, and verified by a Ledger session. These are separate facts; registration never proves client visibility.

The current project snapshot has no activated MCP resource. This work must not select the web-bound backend specialization merely to fill that gap. The design uses the existing Runtime facade and records visibility separately in initialization status and its verification artifacts.

No marketplace, remote provider discovery, generic multi-provider manager, or automatic global activation is included.
