# Alpha3 maintenance tests before independent review

All four native implementation contributions completed and were collected with
exit0. Primary performed registered QA after their scoped handoffs. The reviewed
candidate contains 26 owned files; its exact SHA256 manifest is
[source-candidate-r2.json](source-candidate-r2.json). Main contains only the new
command/parser registration delta from the accepted base. Foreign OOP54-55 bytes
remain outside the candidate and preserved in the working tree.

| Check | Actual result |
| --- | --- |
| New component/CLI/integration suite, branch instrumentation | 136 passed, 6 skipped, 65 subtests passed |
| Whole tests regression in the clean candidate | 514 passed, 7 skipped, 143 subtests passed |
| Added real Windows junction test, separately in the final candidate | 1 passed; all five CLI operations refused the reparse point |
| Existing migration smoke after owner-target adaptation | PASS: dry-run, skip, original bytes/IDs, repeat, conflict, drift, interrupted retry |
| New owner coverage | 93.16% statements, 87.35% branches; 91.77% combined |

Six component skips require unavailable symbolic-link privilege; the additional
existing whole-suite skip concerns creating an interpreter symlink in the shared
QA launcher test. Real NTFS junction creation and all five refusal paths passed.
The junction test was added after the whole-suite run; production files stayed
unchanged and the added test passed separately against the final candidate.

The seven original task criteria are covered by WAL/concurrent snapshot tests;
backup/manifest/hash/integrity/restore checks; exact NUL/CRLF/no-newline quarantine
with source/line/offset/length/hash; explicit refusal/skip and exact counters;
duplicate/conflicting/native identities; source drift and verified semantic replay;
batch rollback, incomplete barriers, explicit retry and verified pre-import backups;
and EN/RU operator recovery documentation. No live project journal was imported.

Actual command/exit/time/log hashes are indexed in
[qa-receipts-r1.json](qa-receipts-r1.json); exact private command lines and raw logs
remain in scoped scratch. Coverage denominators are in
[coverage-summary-r1.json](coverage-summary-r1.json). Whole public release and full
archive/consumer qualification remain pending; these results are source QA.
