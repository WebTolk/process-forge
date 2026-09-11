import json
import shutil
from pathlib import Path
out=Path(__file__).resolve().parent
state=json.loads((out/'final-state.json').read_text());assert state['result']=='PASS'
old=(out/'integration-report.md').read_text()
(out/'integration-before-delivery.md').write_text(old)
(out/'integration-report.md').write_text('''# F09-F12 delivered and installed

Result: PASS within the defined remediation and local-delivery scope.
Commit/source/origin-dev/installed manifest: 901d0551773fe7a5b382b89ebe95b212b0747e83. Version remains 1.1.0; this is a dev update, not a public release.

## Changes
- F09: missing unchanged owned files are restored from the validated archive; read-only plan exposes restored paths, prior absence is journaled, nonregular paths and unknown parent obstructions block even with force.
- F10/F11: overlapping sources produce one document per resource/path; explicit files and file roots honor include/exclude; fulltext content survives metadata overlap; schema-3 derived indexes are rejected and rebuilt by maintenance to schema 4.
- F12: durable per-shard offsets replace repeated historical raw decoding. Windows appends use binary mode. Raw/index/checkpoint crash boundaries, restart, unrelated next event, native conflict, malformed records, multi-shard loss/truncation and forced-recovery combinations are checked.

## Evidence
- baseline-results.json: original four failures reproduced at 52774e4 (20 ingress events decode 190 historical records).
- f09-primary-fixed-tests.json, search-primary-final-tests.json, ingress-post-review-gap-tests.json: final targeted and related source regressions PASS. 20 and 100 new ingress events with/without native IDs decode zero historical records; 20 concurrent processes produce 20 records.
- source-release-targeted.txt: six selected release checks RESULT PASS. Final forced-recovery follow-on covered by ingress-post-review-gap; checksums regenerated and checked before commit.
- source-runtime-integration.txt: genuine Runtime central raw-first ingress E2E PASS.
- archive-quick.txt: archive verification and extracted quick release tests terminal RESULT PASS; archive-focused.txt: all four additional extracted focused tests PASS.
- update-plan.json: 3 added, 5 changed, 0 missing/local-modified/blockers. update-apply.json: applied core-update-20260910T121500Z, post-update doctor PASS, backup retained.
- installed-tests.json: five installed regression/related smokes PASS. Installed search rebuilt (85 resources/documents), doctor and update doctor PASS.
- installed-raw-preflight.json: 7453 actual legacy records / 51673894 bytes validated without mutation. installed-live-ingress.json: two private diagnostic events, duplicate detection and zero historical decoding, no normalized routing. Checkpoint already existed at live probe start; do not describe its zero migration counter as a measured full migration.
- final-state.json: 942 owned files verified, 349 original Workplace semantic files and 10 unowned Core semantic files unchanged; Runtime PID 14080, ready, zero workers/jobs, no scheduler error.

## Orchestration and review
Four gpt-5.6-luna PF codex-exec workers exited 0. Implementation ownership disjoint; primary corrected fixtures and acceptance gaps, reviewers ran only after implementation. Independent bounded review PASS with limitations (f0912-review/report.md). Reviewer sandbox dynamic attempts failed with WinError 5; primary owns genuine executed evidence. Search/ingress/reviewer collection rejected transcript cardinality; original reports/transcripts retained and explicit primary task-complete used, without waivers or fabricated collection success. All four shell assignments done and shell run completed. Parent carrier closes through work-transition evidence.

## Remaining boundaries and next tasks
1. Connected MCP pf.context still says stale for ctx-20260910-113559-b35a98, while current source CLI says fresh/ready. Reproduce the classification/context difference before altering infrastructure; saved connected-mcp-final.json and source-context-final.txt.
2. Investigate reproducible worker-run-collect report/transcript cardinality failures; successful worker exit must not imply successful collection.
3. Full public release qualification remains outstanding; previously intermittent Runtime startup fixture failure was not reproduced by this source E2E and extracted quick suite. These passes are not a full-suite claim.
4. Partial out-of-band removal of individual ingress index files while retaining its checkpoint is not covered by crash recovery. Valid checkpointed raw bytes are not rehashed every event; per-event metadata work remains proportional to shard count. Native symlink fixture unavailable (WinError 1314); directory/parent obstruction tests passed.
5. GitHub #4/#5 remain open; no comments/closure/public release were requested or performed. Historical unrelated PF runs/files preserved.

The clean candidate worktree was removed after verification. Private worker fixtures and scripts under .pf/tmp/f09-update, f1011-search and f0912-review are retained as diagnostic evidence of sandbox/collection issues; prior retained fixtures were untouched.
''')
(out/'iteration-record.md').write_text('''# Immutable accepted iteration record
2026-09-10: baseline F09-F12 reproduced; three junior PF shell implementations; primary fault/compatibility corrections and actual acceptance; independent bounded review; source release gates; commit/push 901d055; clean archive/extracted verification; installed update and real journal/search/Runtime verification; preservation/final-state PASS. Four shell assignments done, shell run completed. See integration-report.md and final-state.json for final results; original worker reports, failures and audit retained.
''')
(out/'summary.md').write_text('''# Run summary
F09-F12 repaired, committed/pushed to dev as 901d0551773fe7a5b382b89ebe95b212b0747e83 and installed locally by core-update-20260910T121500Z.
Source/archived/extracted/installed scoped checks PASS. Core 942 owned files match; 349 Workplace and 10 user Core files preserved. Runtime ready on new PID 14080.
Independent bounded review PASS; primary supplied dynamic acceptance. All shell tasks completed; collection cardinality failures handled by explicit primary acceptance with original evidence preserved.
Next: connected-MCP/source context disagreement, shell report collection cardinality, eventual full public release qualification. Partial out-of-band ingress cache deletion and unavailable native symlink fixture remain explicit test boundaries. See ../../handoffs/core-f09-f12-20260910.md.
''')
Path('.pf/handoffs/core-f09-f12-20260910.md').write_text('''# Handoff: F09-F12 remediation and local delivery

Objective: Continue audited fixes with junior PF shell workers, publish dev, update/test installed PF.
Current status: delivered. Source, origin/dev and installed manifest commit 901d0551773fe7a5b382b89ebe95b212b0747e83. Installed Core 1.1.0 dev; update core-update-20260910T121500Z, backups retained. Runtime PID 14080 ready.
Input artifacts: .pf/artifacts/core-f09-f12-20260910/integration-report.md, final-state.json, review-addendum.md, source/extracted/installed results; original .pf/artifacts/python-core-audit-20260908/report.md unchanged.
Files changed: core_update.py, local_resource_search.py, raw_ingress_kernel.py, release registration, three regression smokes, checksums. Eight public files committed; local PF records intentionally retained separately.
Files not to touch: approved historical audits/capsules, unrelated dirty PF projections/history, installed user semantic files, update backups and diagnostic evidence.
Validation: targeted source and related tests, independent bounded review, source release gates, clean archive plus extracted quick/focused tests, installed five tests, actual private raw acceptance/dedup, common search rebuild/doctor, update doctor, manifest and semantic preservation PASS. 20/100 new events decode zero old raw records. Full release qualification not claimed.
Known issues: connected MCP pf.context stale versus source CLI fresh for same snapshot; three worker collection transcript/report cardinality failures (workers exited 0, tasks explicitly completed by primary); historical intermittent full-suite Runtime startup failure. Partial external deletion of individual ingress indexes with intact checkpoint is outside covered crash contract. Native symlink fixture unavailable (WinError 1314).
Next recommended action: start a new governed diagnostic/remediation run for source/installed MCP context discrepancy and collection cardinality, using these concrete outputs; do not resume unrelated historical runs based on stale MCP recommendations. GitHub #4/#5 remain open, no external messages posted.
Required checks for future release: clean full source/archive/extracted qualification, Runtime failure logs captured before fixture cleanup; exact installed manifest/remote SHA and preserved Workplace.
''')
scripts=out/'scripts';scripts.mkdir(exist_ok=True)
shutil.copy2('.pf/tmp/setup-f0912.py',scripts/'setup-f0912.py')
with Path('.pf/logs/core-f09-f12-20260910.md').open('a') as log:
    log.write('\n## 2026-09-10 12:20 UTC - primary\nDelivery/acceptance: final-state PASS, source/dev/installed 901d055, archive/extracted PASS, installed five smokes PASS, update/search doctors PASS, actual private journal acceptance/dedup PASS. Core 942 owned files and 349 Workplace/10 user Core preservation verified. Runtime restarted PID 14080 ready.\nBoundaries: connected MCP context stale remains despite source fresh; worker report cardinality and full release qualification recorded for follow-up. Candidate worktree removed within verified .pf/tmp bounds; worker fixtures retained as diagnostics.\nNext: close carrier via immutable iteration/result/review/summary/handoff evidence; verify doctors/status.\n')
print('Final artifacts written')
