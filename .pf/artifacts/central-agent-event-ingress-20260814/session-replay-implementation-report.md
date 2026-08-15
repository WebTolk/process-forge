Implemented the assigned replay slice.

Changed files:
- [session_replay.py](D:/Dev/process-forge/tools/pf_runtime/session_replay.py)
- [smoke_central_event_replay.py](D:/Dev/process-forge/tools/smoke_central_event_replay.py)
- [session-replay-implementation-report.md](D:/Dev/process-forge/.pf/artifacts/central-agent-event-ingress-20260814/session-replay-implementation-report.md)

Checks:
- `python -m py_compile tools/pf_runtime/session_replay.py tools/smoke_central_event_replay.py` passed.
- `python tools/smoke_central_event_replay.py` passed.
- Static check found no `argparse`, `chat`, `transcript`, or public replay surface in the new code.
- `git diff --check` passed, with only pre-existing line-ending warnings on `host.py` / `codex_hooks.py`.

Regression note: `tools/smoke_central_event_ingress.py` is blocked before product code by Windows/Python `TemporaryDirectory` permission errors, including with repo-local `TMP`/`TEMP`. I did not edit it because it is outside this worker’s writable scope.
