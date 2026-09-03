# Codex worker output-parent recovery

Status: done

## Problem

The final independent Runtime reviewer completed successfully and emitted a substantive `# WARN` report to stdout, but `codex exec --output-last-message` could not create its target because the expected report directory did not yet exist. `worker-run collect` correctly marked that missing output as failed.

## Change

`tools/codex_exec_worker.py` now creates `output.parent` before launching Codex. The fake Codex smoke fails if that directory is absent, so it verifies the wrapper rather than masking the condition itself.

The final worker stdout has been copied unchanged into `.pf/artifacts/runtime-final-independent-review-20260814/runtime-final-independent-review.md`; its runtime evidence remains in the corresponding `stdout.log` and `exit.json`.

## Verification

- `python -m py_compile tools/codex_exec_worker.py tools/smoke_codex_exec_worker.py` — pass.
- `python tools/smoke_codex_exec_worker.py` — pass.
- `python tools/validate-process-forge-schemas.py --root .` — pass.
- `git diff --check` — pass; only pre-existing line-ending notices.

## Follow-up

The independent report has two actionable findings in `tools/pf_runtime/service.py`: startup lock/liveness coordination and stop behaviour for a live PID before endpoint publication. Fix them in a dedicated Runtime correctness task with concurrency regressions.
