# Code Review: Multi-Process Work Capsule Stability

Verdict: accepted.

Checked changed surfaces: `ProcessExecutionService`, Garage bootstrap/context projection, Core CLI parser and snapshot builder, MCP tool schema, public schemas, documentation/templates, release checksum inventory, and the focused smoke.

Findings addressed during review:

- `_stable_ids` handles a list without attempting to hash it.
- A mapping default outside `allowed` no longer silently broadens authorization.
- Terminal response includes a persisted handoff path when one was created.
- Both inline process transitions and `.pf/process-routes.yaml` can recommend only allowed next processes.
- The focused smoke registers temporary directories for cleanup.

Validation: Python compilation, schema validation, checksum check, event validation, project doctor, focused multi-process smoke, and affected existing Work-start/state smokes passed.

Review method: source-level review by the primary agent; no claim of a separate human or agent reviewer is made.
