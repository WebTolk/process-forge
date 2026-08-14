# PF Long-Lived Runtime Log

## 2026-08-13T18:00:00Z - Codex - scope loaded

- Task: Execute `задания/process-forge-long-lived-runtime-master-prompt.md`.
- Analyzed: `.pf/AGENTS.md`, `.pf/process-forge.yaml`, master prompt, current git status, prior runtime-director-ledger PoC artifacts, and Codex events reference.
- Status: Confirmed requested shape is a user-mode, workplace-scoped, long-lived local runtime with loopback IPC and Core delegation.
- Follow-up: Keep `runtime-host` as fallback/compatibility path.

## 2026-08-13T18:20:00Z - Codex - implementation

- Task: Promote lazy host into process lifecycle and IPC host.
- Changed: `tools/pf_runtime/service.py`, `tools/pf_runtime/host.py`, `tools/processforge.py`.
- Status: Added `pf runtime serve/start/stop/restart/status/doctor/event/session-register/project-state/work-state/resolve/tick`.
- Follow-up: Runtime process uses `workplace/runtime/pf-runtime/service.json`, `runtime.lock`, `token.json`, and logs; state cache remains file-backed only for durable handles, not a RAM source of truth.

## 2026-08-13T18:35:00Z - Codex - smoke coverage

- Task: Add proof for lifecycle, singleton, stale recovery, IPC auth, session isolation, scheduler delegation, crash/restart, fallback, and version mismatch.
- Changed: `tools/smoke_long_lived_runtime.py`, release-test command registry in `tools/processforge.py`.
- Status: `python tools/smoke_long_lived_runtime.py` passed.
- Follow-up: Full `release-test` still needs a longer gate window; checksum inventory may remain stale from pre-existing changes.
