# Final validation

Date: 2026-08-21

Passed:

- `python tools/smoke_runtime_ledger_hooks_mcp.py`
- `python tools/smoke_processforge_core_package_bootstrap.py`
- `python tools/smoke_central_event_ingress.py`
- `python tools/smoke_central_event_replay.py`
- `python tools/smoke_conversation_completeness.py`
- `python tools/smoke_codex_integration.py`
- `python -m py_compile` for changed Runtime modules
- `git diff --check`
- `python tools/processforge.py events-validate --project-root .`

`doctor-project` remains failing only on pre-existing linked-project onboarding
artifacts (package draft, launcher, first assignment and onboarding reports).
It is unrelated to this MCP slice and was not modified.

Not claimed: actual installation/trust of hooks or MCP in the user's Codex host.
Those are opt-in operational steps verified by `codex mcp list`/`/mcp` and
`/hooks` after installation.
