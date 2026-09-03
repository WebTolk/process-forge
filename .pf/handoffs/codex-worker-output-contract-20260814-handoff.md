# Handoff: codex-main -> shell-worker-runtime-final-review

Objective: Obtain an actionable independent Runtime correctness report through the repaired codex-exec delivery contract.

Current status: the worker final response is explicitly defined as the expected report artifact; its smoke passes.

Input artifacts: `.pf/artifacts/codex-worker-output-contract-20260814/output-contract-report.md`; `.pf/artifacts/runtime-general-line-20260814/runtime-correctness-report.md`.

Files changed: `tools/codex_exec_worker.py`, `tools/smoke_codex_exec_worker.py`.

Files not to touch: all Runtime product files are read-only for this reviewer.

Known issues: two prior reviews produced non-actionable conversational output because the delivery contract was implicit; do not treat their alleged defects as verified.

Required checks: return only Markdown report content; include exact file/function/line, reproduction, impact, evidence for every finding, or an explicit pass.

Next recommended action: launch a single read-only `gpt-5.3-codex-spark` review and collect its stdout artifact.
