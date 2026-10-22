# Assurance: MCP/CLI alpha2 verification

2026-10-22. Existing commands were exercised against source HEAD
26dab5ad6783ce0aa56828f86d7f9453e626c638 and installed clean source
fe0f15072538fee9525792ae5b8c1e634b13a928. The main checkout contains pre-existing
unrelated WIP; source CLI evidence qualifies that checkout, while installed
manifest/hash evidence independently qualifies the installed distribution.

| Operation | Result |
| --- | --- |
| source and installed `version` | exit 0, ProcessForge 1.3.0-alpha2 |
| source and installed `project-context-check --project-root <project> --json --strict` | exit 0, fresh/continue, ready, same snapshot/hash |
| actual connected `pf.context` | fresh/continue, same snapshot |
| source, installed and connected MCP `actions list`, query usage, limit 30 | exit 0 / ready; entire parsed envelopes exactly equal; 10 commands and all schema hashes equal |
| connected `pf.actions.describe`, cli:usage summary | ready; current native parser arguments returned |
| source and installed `usage summary --project-root <project> --json` | exit 0; entire parsed envelopes equal after removing only as_of |
| source `usage details --project-root <project> --kind usage --limit 3 --json` | exit 0; three real task-bound records; totals agree |
| installed `core-update status --core-root <installed-core>` | exit 0, installed alpha2, 1476 files, incomplete_update=false |
| all managed files SHA-256 vs installed manifest | exit 0; 1476 files, zero missing/mismatched; manifest path containment checked |
| installed `server status --workplace <workplace> --json` | exit 0; health/readiness ready, five scheduler jobs fresh/ok |
| actual MCP process observation | installed entrypoint, started after update, connected new usage parser/schema matches current CLI |
| previous exact `pf.work.state` | run_completed, valid immutable capsule, no blockers |
| new report-only Work via connected MCP, source CLI work-state | exact run/assignment/context and readiness agree; no product grants |
| Work resolve/search | ready; correct immutable provenance; metadata-only project artifacts; usage accounting query returned zero matches |

The JSON equality checks and integrity results are saved in evidence.json.
No imported or synthetic records were added to the real statistics. Earlier
replay/worker qualification remains previous delivery evidence, not a new run.

Findings and coverage are fully described in report.md: fixed 1.2.0 metadata,
unknown explicit connected build, future MCP usage query transport, partial
accounting/metrics/temp observations, and stale derived project reports.
The current MCP process is consistent with the updated installation, based on
entrypoint/start time, installed integrity and matching catalogue. No in-memory
module hash inspection was performed.

Python implementation was not changed. pytest, Ruff lint/format and mypy for a
changed implementation are not applicable; the read-only functional checks above
are the acceptance tests. No stable/public suite, ZIP re-audit, Kimi native capture,
new worker, installation, restart, repair, refresh, import or replay was run.

Rejected probes: --version is not this CLI's version command; it returned exit 1
and was corrected to documented version. A scope preview with private absolute
paths returned private_path_forbidden without creating a Work; project-relative
artifact-only scope then created one valid Work. A guessed capsule location was
corrected by reading the exact assignment_capsule field. These are probe/setup
corrections, not product defects or permission overrides.
