# Explicit initialization bindings

The shared initialization request now accepts explicit platform,
specialization and process selections from CLI and controlled MCP. CLI flags
are repeatable `--platform` and `--specialization`, plus `--process`; MCP
accepts `platforms`, `specializations` and `process` only in its strict
initialize allowlist.

The Core normalizes these values into the existing answers model, and the
existing project-file builder persists `process` and `specializations` in the
public project manifest. Existing snapshot resolution consumes them from that
manifest. MCP adds no resolver or binding-composition logic.

Verification passed with a greenfield workplace/project fixture using
`--process software-feature-development --specialization backend-developer`:
the generated manifest contained both explicit selections. The full isolated
MCP stdio smoke and `git diff --check` also pass.
