# Tests of the final cumulative alpha3 candidate r4

[Candidate manifest](source-candidate-r4.json) pins 30 public source/test/docs
files and four prior distributions removed only from future Git tracking. Their
exact original local files are preserved; all foreign WIP guards remain required.

The complete registered pytest run in the clean source candidate passed:
**530 passed, 7 skipped**. It includes all maintenance cases and seven new lazy-root
cases. The existing evidence validation smoke separately passed all **10 tests**.
An earlier focused authoring/evidence run passed 111 cases. The seven skips retain
the previously documented symlink-privilege/launcher limits; real Windows junction
refusal remains an executed passing maintenance case.

Registered cumulative candidate Ruff lint and format passed (18 Python files
formatted), strict mypy passed for eight typed production owners, and Bandit
reported zero findings over 2415 lines, without nosec skips. Unchanged legacy
migration/smoke scripts retain their prior lint/format receipts and exact r3 bytes.

[QA receipts r3](qa-receipts-r3.json) pin current final-run logs and native smoke.
Maintenance production bytes are unchanged from the separately measured
145-pass component/65-subtest coverage run. Its statement/branch measurements
remain historical measurements of those identical owners, not a newly measured
coverage run of the added evidence prerequisite. See the retained
[coverage summary](coverage-summary-r2.json).

The first complete public source attempt failed on the pre-existing eager root
and four tracked old dev distributions. Its exact logs/receipts/native report are
retained. Fresh independent review, repair commit/push and repeated complete
public source/full archive-consumer gates remain pending at this checkpoint.
