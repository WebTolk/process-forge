# Orchestration

## Work identity

- Run: `garage-implement-evolve-20261002-28-clarify-and-fix-timeout-scale-propag`
- Assignment: `implement-evolve-20261002-28-clarify-and-fix-timeout-scale-propagation-f`
- Context: `implement-evolve-20261002-28-clarify-and-fix-timeout-scale-propagation-f-capsule`
- Context checksum: `sha256:34947a1a6bcf57281e148b84919fb916b5fdf68c516b88f33d09efc1431837af`

## Task record

Implement `evolve-20261002-28`: clarify and fix `timeout-scale` propagation from `release-archive-test` into extracted `release-test`, with focused tests and documentation/help alignment.

## Execution context summary

The project context is fresh and ready. The previous stale diagnostic writer that held `tools/processforge.py` was closed using existing successor evidence before this Work was created. This Work is pinned and has explicit write scope for `tools/processforge.py`, a focused smoke, documentation/checksum files if needed, and its PF artifacts/log.

## Lifecycle mode decision

Use the standard `software-feature-development` lifecycle. Keep the change narrow: investigate the current timeout plumbing, design the least invasive parameter contract, implement product/test/doc updates, then run focused verification. No Runtime, MCP, installed Core, host restart, release publication, or external infrastructure action is in scope.
