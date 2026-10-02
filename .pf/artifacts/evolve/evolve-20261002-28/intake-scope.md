# Intake And Scope

## Brief

`release-archive-test` exposes `--timeout-scale`, but the current backlog says the extracted `release-test` command does not receive the same per-check scale. This can make CLI help misleading and can leave extracted archive checks using the default internal budgets while only the outer process timeout is scaled.

## Scope

In scope:

- Inspect the current `release-archive-test` and `release-test` timeout code paths.
- Define the intended contract for per-check timeout scale versus any outer process timeout budget.
- Update `tools/processforge.py` narrowly.
- Add or update a focused smoke that captures the nested `release-test` argv and outer timeout.
- Update CLI help and any directly relevant EN/RU documentation if the implementation changes documented behavior.

Out of scope:

- Long release qualification, archive publication, installed Core update, Runtime/MCP restart, or host acceptance.
- Broad refactors of release tooling outside the timeout-scale path.
- Treating a slower run as proof of a hang fix.

## Task Record

Source task: `.pf/artifacts/evolve/tasks-20261002/evolve-20261002-28.md`.
Acceptance checks target default, positive, zero, negative and non-finite values; nested argv capture; outer timeout capture; and documentation/help wording.
