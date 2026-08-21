# Release smoke registration

Status: implemented and verified.

The standard `release-test` registry now includes both public gates:

- `smoke_project_init_local_search_mcp`;
- `smoke_project_init_acceptance`.

Both use a 180-second per-check budget, which is sufficient for the Windows
temporary-workplace fixture while remaining bounded.

Targeted standard runner result on 2026-08-21:

| Gate | Result | Elapsed |
| --- | --- | ---: |
| `smoke_project_init_local_search_mcp` | PASS | 17.01s |
| `smoke_project_init_acceptance` | PASS | 30.20s |

The runner wrote the machine-local report under
`.pf/runtime/release-test/latest-report.{md,json}`.
