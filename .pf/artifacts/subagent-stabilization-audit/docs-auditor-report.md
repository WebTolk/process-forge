# Docs Auditor Report

Read-only native subagent audit. The subagent did not edit files.

## Findings

### Medium: `single-agent tool` wording was ambiguous

The auditor found that `docs/known-limitations.md` described ProcessForge as a
single-agent tool despite current multi-agent assignment/capsule and bounded
supervisor documentation.

Status: fixed. The limitations page now describes ProcessForge as a file-first
CLI with bounded orchestration artifacts and separates unsupported claim/lease
scheduling from supported manual/shell flows.

### Medium: Runtime driver wording needed current neutral driver boundaries

The auditor noted possible confusion around `test-shell-agent` examples and
built-in neutral drivers.

Status: fixed. `test-shell-agent` is documented as a neutral smoke/demo driver,
not a real ecosystem driver.

### Low: Native subagent dogfooding was not separately documented

Status: fixed in the agent runbook and known limitations. Native subagents are
documented as external host-environment executors using ProcessForge
assignment/capsule scope, not ProcessForge runtime drivers.

## Passed Checks

The auditor found no claims that ProcessForge installs skills or slash commands
into `.codex`, `.claude`, `.agents`, or similar folders.
