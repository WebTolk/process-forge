# T04 optional host integration implementation

Timestamp: 2026-09-26 04:04 UTC  
Status: implemented the assigned Core helper and service wiring; focused stub probes pass. No product tests, lifecycle transitions, installation or unrelated file edits.

## API and integration

New `processforge_core.host_integration.optional_host_integration_status(project_root, core)` returns the legacy `codex_integration` status shape with `required: false`, `severity: info`, and `purpose: optional_host_telemetry`. With no callback, expected optional callback failure (`ImportError`, `OSError`, `ValueError`, `SystemExit`), or malformed response it reports a stable unavailable/invalid code and does not expose exception text. Valid compatibility fields are bounded/whitelisted; private paths and arbitrary callback fields are omitted.

`project_initialization.status()` now uses this helper, so a generic Core object without Codex integration status still produces normal generic readiness. The existing `install_codex_hooks` repair action is unchanged: it remains explicit and gated by `apply: true`.

Primary CLI integration instruction: in `tools/processforge.py::execute_project_initialization`, replace the unconditional `project_codex_integration_status(project_root)` call with:

```python
from processforge_core.host_integration import optional_host_integration_status
codex_integration = optional_host_integration_status(project_root, sys.modules[__name__])
```

This preserves the compatibility result while preventing generic onboarding from depending on the optional Codex callback/module. The CLI file is outside this worker’s ownership.

## Evidence and boundary

Ran two focused `python -B` stub probes (after adding `src` to the probe’s import path):

- no callback, each bounded expected exception, malformed response shapes, and a valid legacy response; all returned the required compatibility fields, while exception/path payloads and arbitrary private fields did not escape;
- `project_initialization.status()` on a complete temporary project with a Core stub lacking Codex callbacks returned `state=complete` and optional `codex_integration.status=unavailable`.

The initial probe invocation omitted the repository `src` path and failed at import; the corrected probes above passed. No end-to-end onboarding test was run. In particular, generic CLI onboarding still needs the primary’s direct callback replacement before it becomes independent of a missing Codex integration module. Installed/host qualification remains T06.

## Follow-up: real optional-callback initialization proof

Timestamp: 2026-09-26 (local source-checkout run)  
Status: PASS. Added `optional-init-proof.py` and its captured result `optional-init-proof.json`.

The script loads the actual source CLI module and runs real `project-onboard --apply` and `project-init-status --json` command handlers using isolated temporary workplace/project directories. It patches only `project_codex_integration_status` and exercises four cases: `ImportError`, `RuntimeError`, missing/non-callable callback, and malformed response. All four onboard and status calls returned exit code 0; each project reported `state=complete`, optional integration stayed `unavailable`, no hook file was installed, and private exception/response content did not leak. Invalid response used `optional_integration_result_invalid`; other unavailable cases used `optional_integration_unavailable`.

Terminal run: `python -B .pf/artifacts/t04-provider-adapters-20260926/optional-init-proof.py` — PASS, approximately 25.6 seconds. One initial harness attempt failed while parsing combined YAML+JSON output; the harness was corrected to capture the status command separately and the full run passed. No product files, shared registries, installed hosts, or PF lifecycle state were changed.
