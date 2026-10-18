# Handoff: R01 first-run project-profile search

Status: completed source correction.

The first-run empty corpus is expected when no searchable resource is registered
at the Workplace. `pf.resolve` may still return the selected project profile.
The old smoke incorrectly required search to index that project-local document;
it now tests the real contract and governed work start. See
`.pf/artifacts/r01-first-run-search-20260911/integration-report.md`.

Changed public files: `tools/smoke_user_like_garage_path.py`,
`docs/concepts/garage-core.md`, `checksums/processforge.sha256`.

Validation: user-like Garage, sessionless Garage and project-init MCP smokes
PASS; scoped diff check PASS. The cancelled Luna diagnostic worker has no report
and remains preserved in its runtime record.

R02 (clean release candidate) and R03 (updater concurrency) remain separate
backlog items from the earlier handoff.
