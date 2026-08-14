# Codex worker output-artifact contract

Status: done

## Problem

`codex-exec` writes the final Codex CLI response to the assignment's expected report path. Its launch prompt previously told every worker to write that report, including read-only assignments. The completed independent Runtime reviews therefore returned conversational claims that a report had been saved instead of report content.

## Change

The driver now adds an explicit delivery contract before the immutable capsule: final output is captured verbatim as the expected report; return only the complete report; and read-only workers must not try to write it themselves.

## Verification

- `python -m py_compile tools/codex_exec_worker.py tools/smoke_codex_exec_worker.py` — pass.
- `python tools/smoke_codex_exec_worker.py` — pass; asserts the UTF-8 payload and delivery-contract text received by the fake CLI.
- `python tools/validate-process-forge-schemas.py --root .` — pass.
- `git diff --check` — pass; only pre-existing line-ending notices.

## Next action

Run a new read-only Runtime review. Its `gpt-5.3-codex-spark` final Markdown will now be the durable review artifact.
