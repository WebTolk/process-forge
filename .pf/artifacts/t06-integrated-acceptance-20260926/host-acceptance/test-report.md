# T06 integrated acceptance: source, installed Core and actual connected host

Date: 2026-09-26. Result: PASS for T06 assurance. This supplement supersedes the earlier report's pending installed/host boundary without changing its frozen bytes. Source and installed prerequisite reports remain independent evidence.

## Accepted implementation and connection

Installed candidate: `69110c50559d994d7a31e751b7cd7afc989698db`; archive SHA256 `73b588243ec8bd8ffb9d73ab4dabaa323f62c55f26709ef149f3ef6dd5c4c42e`. All 987 owned installed file hashes match the delivered manifest. The actual application's Python MCP process started at 2026-09-26T12:05:46Z, after delivery; its configured installed entry point is recorded in connected-process-identity.json. Actual request diagnostic records independently report hashes matching installed mcp_server.py and diagnostics.py. New work.search/work.resolve tools are present and were called through this application's connected tool surface.

The actual MCP resumed the original T06 with `continue_existing`, exact original Run/Assignment, code-assurance stage and unchanged legacy capsule SHA256 `8bd7af0ba78c19c7c3aedb3e80d8d45436511ed0fa4090e501b1536dfa5467a6`. Context is fresh at snapshot `ctx-20260925-140110-0dbc7c`, unchanged SHA256 `f73d8d332313f45a99d4e7b943e18bf4e812b44a51d4d8c682e8291b0753a562`. This discharges the genuine application reconnect/continuation boundary from the previous session. No session identity was fabricated and no shared service was restarted.

## Deterministic evidence

- Previous source assurance: 19 distinct passing smokes, schema/public/checksum/link/syntax gates, primary semantic review; see ../test-report.md, ../assurance-results.json and ../final-checks.json. Existing frozen results remain valid because source payload hashes are unchanged.
- Delivered candidate/archive and installed qualification: see ../../t06-installed-delivery-20260926/{candidate-test-report,delivery-report}.md and installed-verification.json. The eight installed feature/transport smokes and separate installed stdio proof remain a distinct layer.
- Actual project reads: fresh context, authorized project-artifact resolve, and denied `docs.api.gitverse:root` with `not_in_project_snapshot`. Existing project search correctly reports no indexed authorized corpus; it is not positive search evidence. A first concurrent resolve timed out at the tool's 60-second limit; the later isolated retry succeeded. Latency/queueing remains an observation, not a diagnosed cause or ongoing outage.
- Actual new Work contract: isolated project-local resources, installed snapshot constructor, actual MCP work.start with valid complete contract, fulltext search with one verified document, and resolve with `verified_declared_material`. Fixture creation never registers a project/package in the global Workplace.
- Actual access negatives: resource_not_in_work, work_context_mismatch, resource_material_changed, resource_access_revoked, resource_not_in_stage. Restoring material/current authorization restores the original pinned read. The old T06 capsule remains `legacy_contract_incomplete` for new Work reads, as required; it was not rewritten.
- Actual five diagnostic profiles: exact search and denial payload parity across quiet/normal/diagnostic/trace/off; all five incomplete transitions enforce required evidence. Quiet retains the expected warning on denied access; off emits no optional diagnostics. There are 51 canonical bounded diagnostic records (44,817 bytes), with no fixture query/body leakage.
- Actual lifecycle: prepare -> build (empty resource subset) -> verify (inherits pinned resources) -> run_completed, all valid transitions while diagnostics are off. The mandatory journal contains the exact three stage completions/transition targets and one run.completed. Fixture capsule bytes are unchanged.
- Preservation: 987 installed files, 983 source payload files, 2,199 pre-existing frozen evidence/context files and 21 config/snapshot files are unchanged (boundary-result.json). The main T06 run-doctor at code-assurance passed all 18 checks. Final completed-run checks follow lifecycle closure.

The saved-response verifier passed 26 assertions: acceptance-result.json, verify_acceptance.py. Raw calls are in bootstrap.json, resource-read-cases.json, profile-cases.json, mutation-cases.json and fixture-lifecycle.json. Fixture events/diagnostics are retained separately. Two verifier assumptions and one command-polling error were corrected against actual documented semantics; their observations are preserved, and no product result was modified.

## Scope and limitations

The host API exposes tool results, not its raw stdin/stdout stream or notification sender. Valid decoded application replies prove usable routing; canonical JSON-RPC-only stdout and silent notification behavior are evidenced by the delivered installed stdio proof, not mislabelled as direct raw-host capture. No real Ledger-bound session exists here: actual missing_session denial passed; session-bound cross-project negative coverage remains the installed isolated integration proof, as allowed by the conditional host-session test. This does not claim host hook/session telemetry acceptance.

Browser/UI verification: not_applicable; no UI change. Public release/full release suite, T07, T10 and UI remain outside scope. Existing unrelated Runtime degraded-health warning remains outside this acceptance.

The completed delivery prerequisite has an open metadata finding: its original objective contained a private installation path. That immutable delivery capsule was not rewritten; its run-doctor is not claimed green. This is separate from original T06 and installed payload validity; see ../../t06-installed-delivery-20260926/closeout-metadata-finding.md.

Assurance decision: applicable source, installed and actual connected-host layers pass. Continue the same T06 through release-delivery/evolve using the delivered prerequisite; no repeat installation or implementation is required.
