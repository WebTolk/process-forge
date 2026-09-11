# F09-F12 primary acceptance before independent review

Baseline: 52774e4761975ce0cb29095081c5294db882007d. Original approved audit is unchanged. All four original failures reproduced in baseline-results.json.

## Implementation and acceptance

- F09 restores missing unchanged owned files, explicitly lists restored paths in the read-only plan, journals prior absence as null, blocks nonregular owned objects and unowned parent obstructions even with force. Primary corrected the worker fixture (its archive wrongly collided with a user file), temporary-directory default, lexical checks, added faults before restoration and after restoration/before manifest. f09-primary-fixed-tests.json: new smoke and full existing core manifest/migration smoke PASS.
- F10/F11 deduplicate by resource identity and relative path, honor explicit-file/file-root include/exclude, retain fulltext content when overlapping metadata exists. Derived schema version 4 rejects old cached orphan/excluded rows, existing maintenance rebuilds them. Primary corrected the test harness and added migration/metadata-overlap/file-root exclusion coverage. search-primary-final-tests.json: four new/related tests PASS; source authorization and common Workplace index behavior preserved.
- F12 per-shard durable byte offsets advance only after raw/native index records are durable. Normal new events do not decode historical raw records; restart and raw/native/checkpoint write failures recover unindexed tails, including an unrelated next event. Legacy journals without checkpoint rebuild indexes once. Primary corrected Windows CRT CRLF expansion using O_BINARY, checks every known shard before recovery (including all-missing), rejects invalid raw identity objects. ingress-primary-final-tests.json: new and existing ingress kernel tests PASS. 20/100 events with/without stable native IDs decode zero historical records/bytes; twenty concurrent processes accepted twenty records.

## Worker provenance

Three requested PF codex-exec shell workers used gpt-5.6-luna (medium updater/search, high ingress), disjoint write scopes. All exited 0. Updater report collected. Search and ingress collection rejected transcript/report cardinality; original reports and transcripts retained, no rewriting. Primary explicitly owns final acceptance and compatibility completion of these two shell assignments. Worker sandbox WinError 5 prevented some dynamic tests; PASS claims above are primary executions, not inferred from worker exit.

## Review remit and boundaries

Review the six source/test files against baseline, plus the three release-list registrations in tools/processforge.py (only those lines; no full CLI read). Focus updater prior-absence/unknown-file safety, search derived migration/counts/authorization/mode ordering, ingress checkpoint/crash/dedup/concurrency. Finish with concrete findings or bounded PASS. No source edits. At most one focused test attempt per area; if sandbox denies temporary file operations, report and stop that attempt.

Ingress metadata work remains proportional to hourly shard count (stat/enumeration/checkpoint map), not historical event count; raw journals are append-only. Wholesale derived-index loss removes checkpoint and triggers legacy rebuild, as covered by the existing test. Partial out-of-band deletion of individual JSON indexes without removing the checkpoint is outside tested crash transitions and must not be claimed covered. Valid checkpointed raw bytes are not rehashed on every event.

Pending: independent review, integration/release checks, clean commit/push dev, archive + extracted acceptance, installed update/regressions/Workplace preservation, runtime reload and governed closeout. No full public release qualification claimed; known intermittent runtime startup fixture failure remains a separate boundary.

## Primary additional fault acceptance during review
A combined fault (unreadable raw index plus another missing checkpointed shard) reproduced an unsafe forced-recovery bypass; evidence force-recovery-gap.txt. Primary now evaluates checkpointed shard integrity before either incremental or forced recovery, with missing_with_bad_index regression. See ingress-post-review-gap-tests.json for final execution. This is a small follow-on delta after the initial primary matrix; final checksums regenerated.
