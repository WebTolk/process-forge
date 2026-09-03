## 2026-08-14 08:03 - codex-main

Task: Clarify how a read-only codex-exec worker delivers its expected report.
Files changed: `tools/codex_exec_worker.py`, `tools/smoke_codex_exec_worker.py`.
Artifacts changed: `.pf/artifacts/codex-worker-output-contract-20260814/output-contract-report.md`.
Templates used: none.
Tools used: ProcessForge CLI, Python `py_compile`, targeted smoke, schema validator.
Decisions: stdout remains the transport; launch text now requires report-only final Markdown and prohibits an impossible read-only file write.
Risks: the contract is verified with the fake CLI; an actual Runtime reviewer must confirm practical output quality.
Next steps: complete this task and launch the final independent Runtime review.
Handoff: `.pf/handoffs/codex-worker-output-contract-20260814-handoff.md`.
