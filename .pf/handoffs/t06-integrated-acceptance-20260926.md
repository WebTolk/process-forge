# Handoff: T06 local acceptance -> installed-host acceptance

Objective: finish r02 T06 integrated acceptance without conflating source tests and updated installed-host behavior.

Current status: T06 remains in_progress at code-assurance; local source integration PASS, assurance-complete intentionally not passed. The user's 2026-09-26 resume supersedes pause-after-t05-20260926.md. This is the current continuation point.

Run: garage-t06-pf-vision-alignment-r02-integrate-acceptance-for-work-resourc.
Assignment: t06-pf-vision-alignment-r02-integrate-acceptance-for-work-resources-norm.
Process: software-feature-development@1.1.0, fingerprint cc411028e9585dd8f56e07faa8997d9e7af1a39a801a0d8c0ca9c8c1e89dfd49.
Snapshot: ctx-20260925-140110-0dbc7c, fresh at actual host/source/installed checks.
Immutable T06 capsule SHA256: 8bd7af0ba78c19c7c3aedb3e80d8d45436511ed0fa4090e501b1536dfa5467a6. It was created by installed T08 Core and is legacy to current source; never rewrite it.

Input artifacts: .pf/artifacts/t06-integrated-acceptance-20260926/{test-report,review-findings,test-plan,implementation,architecture,scope}.md; developer-recovery-result.json; assurance-results.json; final-checks.json; baseline.json; boundary-proof.json; evidence/*.json. Initial harness preflight failure retained separately.

Files changed: tools/smoke_prepared_execution_recovery.py; one registration in tools/processforge.py; checksums/processforge.sha256; EN runtime-drivers/runtime-mcp/declarative-process-execution/garage-core and existing RU runtime-drivers/runtime-mcp/declarative-process-execution docs. T06 artifacts/log/handoff and normal generated Work state only. Product services unchanged by T06; prior source modifications remain uncommitted.

Verification: 19 distinct source smokes PASS including actual process exit/dead-owner recovery, governed offline execution/collection/stdio continuation, Windows Junction, five diagnostic profiles and isolated Runtime/Ledger/hooks/MCP. Source schema/public/checksum/link/syntax gates PASS. run-doctor 18 PASS for active run. All 561 baseline frozen files unchanged. Primary semantic review completed. No full release suite/package/installation claim.

Actual host: fresh context, authorized project-artifact resolve, unselected-resource denial and missing_session honored. Main search returned zero, which is not positive project corpus coverage. Separate source/installed stdio connections kept exact T06 stage/identity and clean protocol without protected state/config mutation. Host process identity saved in evidence; PIDs are historical observations, not restart targets.

Known issue: connected installed Core is still T08. New pf.work.search/pf.work.resolve and work_context/diagnostics modules are absent there. Current-source host feature acceptance is outstanding, including real reconnect and session-bound negatives where a genuine session exists. Existing T06 capsule cannot acquire new grants by install or snapshot refresh.

Files not to touch: all earlier frozen T01-T05/T08/T09 evidence/capsules, unrelated dirty work, external projects, installed/shared Runtime/Core/Workplace absent separately authorized delivery. T07/T10/UI/public release are outside this sequence. No infrastructure repair/restart was attempted.

Next recommended action: inspect fresh PF state and this Work; prepare a reviewable delivery candidate and exact installed diff/backup/rollback under a separate bounded delivery scope. .pf/AGENTS.md prohibits ordinary-agent infrastructure installation/restart. Following appropriate operator authorization and installation, reconnect the actual host and verify current source features using a NEW isolated complete-context fixture (not a rewritten T06 capsule). Attach evidence here and continue the same T06 Work through assurance, release-delivery and evolve. Do not start duplicate T06 or claim run_completed prematurely.
