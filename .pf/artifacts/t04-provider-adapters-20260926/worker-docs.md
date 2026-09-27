# T04 adapter documentation handoff

- Status: complete; bounded documentation task.
- Owned files: `docs/concepts/provider-adapters.md`, `docs/ru/concepts/provider-adapters.md`.
- Source checked: `tools/pf_runtime/provider_adapters.py`, `builtin_provider_adapters.py`, `codex_adapters.py`, `host.py`; `src/processforge_core/host_integration.py` and `project_initialization.py`; accepted T04 scope/domain/architecture.
- Documented the current trusted immutable registry, exact provider/adapter lookup, raw receipt versus derived-effect admission, stable denial codes, split adapter/Host duties, Runtime legacy boundary, optional Codex status, explicit apply-gated repair, and source versus T06 installed/host qualification.
- Included a finite alternate-policy example using the current `AdapterRegistry` and `host.ingest_event(..., registry=...)` API. It is explicitly an integration shape; the prose says a real policy must enforce provider-specific provenance and still pass Host checks.
- Validation: reviewed all three relative links in each guide; paths resolve from their document directories. Checked authored files for trailing whitespace and inspected the final diff. No source, tests, transitions, or other documentation files changed.
- Residual boundary: no tests or installed/connected Host qualification were run; those are outside this docs-only assignment and remain T06 evidence.
