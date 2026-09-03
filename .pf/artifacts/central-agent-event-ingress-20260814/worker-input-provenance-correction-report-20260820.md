# Worker input provenance correction — 2026-08-20

## Result

PASS. `WorkerPromptPayloadSubmitted` now requires a durable, PF-owned input contract in addition to the session, task, attempt and source allowlist.

## Contract

- Before ingress, `codex_exec_worker.capture_worker_input()` writes a private atomic `worker-input-contract.json` in the prepared agent-run directory.
- The contract records `run_id`, `task_id`, `attempt`, repository-relative expected report, payload SHA-256, and the canonical system summary.
- Host recalculates the input hash, requires an exact contract match, and accepts a system message only when its text equals the canonical summary.

## Validation

- `python -m py_compile tools/codex_exec_worker.py tools/pf_runtime/host.py tools/smoke_conversation_completeness.py`
- `python tools/smoke_conversation_completeness.py` — PASS.
- The smoke includes correct PF provenance and session/attempt with an arbitrary safe system summary; it is denied as `untrusted_conversation_provenance`.
- `python tools/smoke_codex_exec_worker.py` — PASS.
- `python tools/processforge.py events-validate --project-root .` — PASS.
