# Evolution Report

## Captured Learning

The backlog item was valid: `release-archive-test` scaled the outer extracted-test watchdog but did not pass `--timeout-scale` into the extracted `release-test` command.

Additional learned issue: `float(getattr(... ) or 1.0)` silently treated explicit `0` as default and did not reject `nan` / `inf` before timeout use. Future timeout-scale options should share a finite-positive validator and must not use truthiness to detect missing numeric values.

## Updated Rules Or Extensions

No global rule file was updated in this Work. The project documentation now states the archive-test timeout-scale contract in EN/RU known limitations.

## Instruction Or Knowledge Update Proposal

No separate knowledge package update is proposed. A later general evolve run may aggregate this as: "CLI numeric scale options should validate finite-positive values and keep nested-command argv propagation covered by focused tests."
