# Tool And MCP Registration

Tools and MCP servers are capability providers stored in workplace registries.

Tools live in `registries/tools.yaml` and describe command-backed capabilities such as builders, linters, validators, generators, and documentation tools.

MCP servers live in `registries/mcp.yaml` and describe MCP capability providers such as official documentation lookup. Secrets are never stored directly; use `auth_ref` names only.

Dry-run commands create proposals. `--apply` updates the registry and emits a workplace event.

## Updates

Tool definitions and tool packages can be update subjects. `replace_file` is
the deterministic MVP apply policy; `custom_command_requires_confirmation` is
blocked by default and ProcessForge does not execute arbitrary remote scripts.
MCP definitions are discoverable update subjects, but provider-specific MCP
installation remains outside the MVP apply surface.
