# Release Auditor Report

Read-only native subagent audit. The subagent did not edit files.

## Findings

### Medium: `public-gate` was listed but not addressable by `--only` or `--skip`

The auditor confirmed that `release-test --list` printed `public-gate`, while
`--only` validation accepted only command labels.

Status: fixed. `public-gate` and `git diff --check` are explicit labels for
`--list`, `--only`, and `--skip`.

### Medium: Extracted archive test did not run the public gate

The auditor confirmed that `release-archive-test` ran extracted `release-test`
without `--public` and with a fixed timeout.

Status: fixed. `release-archive-test` now runs full extracted
`release-test --public` by default and supports `--extracted-test` and
`--timeout-scale`.

### Low: Resource authoring smoke timeout output could still be hard to diagnose

Status: improved. The smoke prints per-test temp paths, per-command start/end
records, elapsed time, and timeout budgets with flushed output.

### Low: `test_no_powershell` checked file suffixes only

Status: accepted for the smoke's scope. Public text cleanliness remains covered
by `validate-public-cleanliness.py`; the smoke now avoids the expensive repeated
fixture setup.
