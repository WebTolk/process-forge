# T06 integrated acceptance result

Date: 2026-09-26. Local source result: PASS. Overall T06 result: INCOMPLETE; updated installed/actual-host feature acceptance is required. Do not satisfy assurance-complete from this report alone.

## Deterministic source evidence

Nineteen distinct smokes passed: the new recovery regression (developer-recovery-result.json) plus eighteen in assurance-results.json. The latter use seventeen registered commands/timeouts and one explicitly supplemental Runtime/Ledger/hooks/MCP smoke. Initial runner preflight failed before any tests because the supplemental check was assumed registered; the corrected run completed with no failed checks. No full release suite, package qualification or installation was performed.

| Contract | Current proof | Result |
|---|---|---|
| Real collector death, receipt/dead-owner recovery, exactly-once events | new smoke_prepared_execution_recovery | PASS |
| Offline executor, governed collection invariance, fresh source MCP continuation/transition | new smoke_prepared_execution_recovery | PASS |
| Actual Windows Junction redirects no private bytes | new smoke_prepared_execution_recovery | PASS |
| Prepared input budgets, authorization/drift, attribution, repeat collection | smoke_prepared_execution_context | PASS |
| Work grants/material/stage intersection and explicit context identity | smoke_work_resource_binding | PASS; direct symlink privilege unsupported, separate real Junction test passed |
| Shared context, immutable intent and capability/scope contract | smoke_work_capsule_contract_parity | PASS |
| Existing worker shell, workspace, Codex, governance and driver registry | five corresponding smokes | PASS |
| Report authentication, containment, transcript completeness | three corresponding smokes | PASS |
| Trusted adapters, central ingress, session identity, JSON-RPC validation | four corresponding smokes | PASS |
| quiet/normal/diagnostic/trace/off process invariance | smoke_diagnostics_process_invariance | PASS; optional records 0/18/23/25/0 |
| Diagnostics privacy/configuration/sink failure/rotation/export/performance | smoke_diagnostics | PASS |
| Isolated Runtime/Ledger/hooks/MCP | supplemental smoke_runtime_ledger_hooks_mcp | PASS, 23.510 s; earlier T09 startup observation did not recur |

Diagnostic measurements: 100,000 disabled calls median 0.110576 s; 10,000 memory records 0.634727 s; 10,000 JSONL writes 12.932200 s. Storage stayed within the 16,384-byte fixture quota. These are bounded source-fixture observations, not host production performance claims.

final-checks.json: syntax and all changed-document relative links PASS; schema validation PASS; public cleanliness PASS; checksum write/check PASS; run-doctor exit 0 with 18 PASS for the still-active run. All 561 baseline frozen evidence/capsule files are byte-identical. Source hashes of all ten T06 product files are recorded. git diff --check passed (existing CRLF normalization warnings only). Semantic review is recorded separately in review-findings.md. Browser verification: not_applicable, because this task changes no UI.

## Actual connection and installed boundary

The application's actual MCP returned fresh ctx-20260925-140110-0dbc7c, resolved authorized project artifacts, returned no T06 search matches from the existing project index, denied docs.api.gitverse:root outside the project selection, and returned missing_session for a Ledger-only view. Do not mistake the empty project search for positive corpus coverage; T08 already recorded this catalogue limitation.

boundary-proof.json compares source and installed CLI and separate new stdio connections: all retain the exact T06 Run/Assignment at code-assurance. Both use JSON-RPC-only stdout, silent notifications, empty stderr and EOF exit 0. Assignment, run, capsule, snapshot and shared Workplace configuration hashes remain unchanged by those read-only probes. This is a separate connection proof, not a reconnect of the application's host connection.

Installed MCP/Host hashes differ from current source, installed work_context/diagnostics modules are absent, and installed/actual tool discovery lacks pf.work.search and pf.work.resolve. The source correctly reads T06's old installed-created capsule as legacy_contract_incomplete; it remains immutable. No production session identity was fabricated. Current-source Work reads, diagnostic profiles and provider integration have not been accepted through the application's updated installed connection. This is the only remaining acceptance layer identified by this run, and it is not waived.

## Continuation

Keep the T06 Work in code-assurance. First prepare a separately governed delivery candidate from the reviewed source, qualify its package and exact installed diff/rollback, then obtain any required installation/operator authorization under .pf/AGENTS.md. After delivery and genuine host reconnection, run the positive and negative Work-resource/profile checks against a newly created isolated fixture with the current complete context contract. Do not overwrite the legacy T06 capsule or fabricate Ledger sessions. Resume this Work and pass assurance-complete only after attaching that evidence; release-delivery/evolve remain unexecuted.
