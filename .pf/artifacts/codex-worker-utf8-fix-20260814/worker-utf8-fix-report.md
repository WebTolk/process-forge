# Codex worker UTF-8 transport fix

Status: done

## Trigger

The independent Runtime reviewer failed before it could inspect code: Codex CLI rejected stdin as non-UTF-8. The assignment contains a Cyrillic source path, and the wrapper previously let `subprocess.run(text=True)` choose the Windows text encoding.

## Change

`tools/codex_exec_worker.py` now encodes the complete prompt payload explicitly as UTF-8 bytes before launching `codex exec`. The command, model selection, workspace grants, output routing, and heartbeat contract are unchanged.

The `smoke_codex_exec_worker.py` fake CLI now reads raw stdin, decodes it strictly as UTF-8, and requires a Cyrillic phrase in a generated assignment. Its failure diagnostics also tolerate supervisor logs not being created.

## Verification

- `python -m py_compile tools/codex_exec_worker.py tools/smoke_codex_exec_worker.py` — pass.
- `python tools/smoke_codex_exec_worker.py` — pass.
- `python tools/validate-process-forge-schemas.py --root .` — pass.
- `git diff --check` — pass; only pre-existing line-ending notices.

## Residual risk

This proves the worker-to-CLI stdin boundary. A real Codex CLI worker must still be relaunched to independently review the Runtime slice.
