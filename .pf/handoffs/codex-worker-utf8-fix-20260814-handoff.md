# Handoff: codex-main -> shell-worker-runtime-correctness-review

Objective: Resume the independent Runtime correctness review after restoring the UTF-8 worker transport.

Current status: the codex-exec wrapper and its Cyrillic regression smoke pass.

Input artifacts: `.pf/artifacts/codex-worker-utf8-fix-20260814/worker-utf8-fix-report.md`; `.pf/artifacts/runtime-general-line-20260814/runtime-correctness-report.md`.

Files changed: `tools/codex_exec_worker.py`, `tools/smoke_codex_exec_worker.py`.

Files not to touch: Runtime source and tests remain read-only for the reviewer.

Known issues: the first reviewer run failed solely on non-UTF-8 stdin and produced no review; full `doctor-project` has unrelated historical onboarding failures.

Required checks: start `codex-exec` with `gpt-5.3-codex-spark`, collect its report, and assess only concrete Runtime findings.

Next recommended action: create a replacement read-only review assignment and run it through the repaired `codex-exec` driver.
