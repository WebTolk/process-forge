## 2026-08-14 07:56 - codex-main

Task: Repair the Windows text-encoding boundary exposed while starting the independent Runtime reviewer.
Files changed: `tools/codex_exec_worker.py`, `tools/smoke_codex_exec_worker.py`.
Artifacts changed: `.pf/artifacts/codex-worker-utf8-fix-20260814/worker-utf8-fix-report.md`.
Templates used: none.
Tools used: ProcessForge CLI, Python `py_compile`, schema validator, targeted smoke.
Decisions: pass UTF-8 bytes explicitly to `codex exec`; do not change Runtime domain behavior or worker command arguments.
Risks: a real worker review remains required; `doctor-project` historical onboarding debt is out of this task scope.
Next steps: complete this task and start a replacement read-only independent Runtime review.
Handoff: `.pf/handoffs/codex-worker-utf8-fix-20260814-handoff.md`.
