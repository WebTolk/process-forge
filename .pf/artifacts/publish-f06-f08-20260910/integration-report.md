# Publication, F06-F08 repair and installed update

Accepted scope: F06-F08 and local update/test. Final source, origin/dev and installed Core manifest all identify `52774e4761975ce0cb29095081c5294db882007d` (VERSION remains 1.1.0). Earlier accepted F01-F05/documentation/required-output changes were committed and pushed as `5c95391` first, as requested.

F06 uses a persistent native OS guard across acquisition, dead-owner recovery and release. Live/unknown/foreign owners are retained; owned metadata is removed only with its matching token. F07 handles presence JSON and preserves the active organized-session Director restriction. F08 shares the report-default helper across task lookup and normalization.

One junior PF shell implementation was stopped after sandbox limitations; primary took over, fixed the reaper race/Win32 handle declarations and completed the assignment explicitly. A separate junior shell reviewer returned bounded PASS and durable exit 0, then was collected DONE. See f0608-cli/report.md, f0608-review/report.md and review-addendum.md. No stopped worker success is claimed.

## Validation

- All three defects reproduced on 5c95391; public-copy positive and old-CLI negative controls recorded.
- Expanded smoke passes with real processes, 32 mutually exclusive updates, crash recovery, unconditional foreign/malformed ownership checks and actual CLI routes.
- Existing registry safety, authoring recovery, coordination, task batch and orchestrator shell-agent checks pass. Final targeted release test: RESULT PASS.
- Schema, checksum and public cleanliness pass. Both clean-commit archives pass manifest/source parity and extracted quick release tests, RESULT PASS.
- Installed 5c95391 search, evidence and completion smokes passed. Installed 52774e4 F06-F08 smoke and update doctor pass; automatic post-update Workplace doctor passes.
- All 939 installed owned files match the final manifest; all 346 original semantic Workplace files remain byte-identical. Ten unowned Joomla process files were preserved, so a generic public inventory check reports extras. No owned mismatch was found.
- Runtime was restarted through its CLI after verifying zero workers/jobs. New PID 12860 is ready, no scheduler error or pending jobs; old PID was 2200. final-state.json records exact provenance and archive hash.

## Remaining boundaries

F09-F12 remain open. The full-source candidate run failed at intermittent Runtime startup in central ingress; standalone long-lived and five subsequent diagnostic ingress checks passed. Its cause is unresolved, so no full source/full extracted or public-release qualification is claimed. POSIX flock behavior was not executed on this Windows host. Non-cooperating old writers that do not use the permanent guard remain outside the new protocol.

The connected long-running MCP still reports this source repository snapshot stale, while fresh installed CLI/MCP test fixtures work. The disk/runtime update does not prove that every app MCP client reloaded its imported modules. No GitHub issues were edited or closed.

All PF historical/private files remain local and preserved. Final lifecycle proof is closeout.json; handoff is .pf/handoffs/publish-f06-f08-20260910.md.
