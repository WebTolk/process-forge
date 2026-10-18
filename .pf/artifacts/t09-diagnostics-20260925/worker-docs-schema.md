# T09 diagnostics docs/schema handoff

Changed only the assigned product files:

- `schemas/diagnostics.schema.json` — version 1 JSON configuration contract for `DEFAULTS`, hard field ceilings, `locked`, and identity-keyed `work`/`sessions` override maps.
- `docs/concepts/diagnostics.md` — English configuration and operator guide covering optional-vs-mandatory boundaries, levels, profiles, expiry, precedence, limits, sinks, health, export, CLI surface, and source/installed distinction.
- `docs/ru/concepts/diagnostics.md` — matching Russian guide with the same examples and command syntax.

Source alignment: schema values mirror `src/processforge_core/diagnostics.py` constants and configuration layering. Runtime still enforces per-layer downward-only limits, locked values, and cross-field fit; JSON Schema alone cannot express those comparisons. The CLI commands are present in source; the docs retain the source/installed distribution distinction. Export wording reflects local filtered/sanitized exclusive-create behavior; it does not promise upload, repair, restart, or installed availability.

No source changes, tests, transitions, or installation were performed, as scoped. Serena/IDE was unavailable as recorded in T09 scope; implementation details were read directly from the named source module and architecture artifact.

Follow-up: schema now accepts timezone-aware ISO 8601 offsets and docs specify UTC-instant expiry comparisons. Clarified fail-closed `off` fallback with fixed stderr health notice, current-process counters and canonical-record snapshots, canonical stderr output for `PF_CODEX_HOOK_DEBUG`, and implemented-in-source CLI commands with an installed/source distinction. No tests were run.
