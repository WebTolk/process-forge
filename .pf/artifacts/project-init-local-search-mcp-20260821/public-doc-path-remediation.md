# Public documentation path remediation

Status: implemented.

`docs/concepts/codex-session-read.md` used a Windows absolute-looking example
path in an otherwise portable MCP registration command. It now uses the
explicit non-filesystem placeholders `<processforge-install>` and
`<processforge-workplace>`, preserving the command structure without leaking
or syntactically resembling a machine-local path.

This unblocks the release public-cleanliness gate.
