# A01-A11 execution record

Date: 2026-09-11. Primary orchestrator; source baseline
`901d0551773fe7a5b382b89ebe95b212b0747e83`, VERSION 1.1.0.

The user authorized source remediation through PF junior shell workers.
`design.md` precedes implementation. Existing audit artifacts and capsules
were preserved. Chronological records: `.pf/logs/core-a01-a11-20260911.md`.

| PF child run | Work and ownership | Terminal task evidence |
| --- | --- | --- |
| core-a01-a11-wave1-20260911 | A09 CLI classification, A01 search, A03/A04/A10 Runtime; three disjoint codex-exec workers on gpt-5.6-luna/high | All exited 0, collected, DONE. Primary subsequently integrated Runtime liveness, degradation, fault isolation and common singleton guarding. |
| core-a01-a11-wave2-20260911 | A02/A06 reports, A05 migration, A08 MCP | Initial three workers failed backend 403 before edits; evidence preserved. One bounded A05 retry exited 0 and was collected. Primary completed A02/A06 and A08 after failed ownership handoff, explicitly attributed as fallback. |
| core-a01-a11-wave3-20260911 | A07 sessions, A11 lifecycle; disjoint CLI/hooks ownership | Both exited 0 and collected. Primary closed legacy presence/chat compatibility gaps, fixed lifecycle test bootstrap and removed undocumented provider-ID trust. |
| core-a01-a11-review-20260911 | Two read-only Luna reviewers after implementation | Both exited 0 and collected. Primary resolved all four concrete findings; original conditional reports remain intact. |

Quality control used original-HEAD counterexamples and current real CLI/MCP,
collector and Runtime checks. All 11 new registered regression scripts pass
current source and fail original HEAD for the tested defects. Evidence and
prior failed attempts remain under `validation/`.

Full-suite expansion found an old single-agent test hardcoding the previous
presence filename. Primary updated it to inspect exact stored identity and
verify checkout produces one terminal presence record. The updated test passes.
Full-suite completion remains an assurance activity; implementation is complete.

All child summaries/handoffs were generated and runs completed sequentially
through the source CLI. The pinned main Work continues through PF MCP.
No commit, push, installed update, service restart or publication occurred.
