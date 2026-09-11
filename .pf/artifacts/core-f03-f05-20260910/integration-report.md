# F03-F05 remediation integration report

Status: F03-F05 accepted after primary validation and independent assurance/review. Governed terminal states are recorded in closeout.json.

## Scope and delivery

Base HEAD remains `1aecc18b6824204ca45ab30241b92d26e6d583a5`. Existing F01/F02, documentation and required-output fixes are preserved. No commit, publication, version change or installed Core/Workplace operation occurred.

- F03: newest applicable evidence is selected before status evaluation. Input/artifact aliases share identity; required evidence IDs remain distinct. Current-stage output and exit-gate scope is preserved on reentry.
- F04: depended-on file evidence is re-resolved inside the project, checked as a file and compared with its stored digest during readiness and transition. Missing/changed/unsafe/unreadable/missing-digest proofs become unsatisfied with diagnostics. Obsolete unrelated evidence and pathless attestations remain supported.
- F05: an atomic completion intent precedes terminal writes. Ordinary transition/complete retries discover and replay it under the run lock, including when statuses are already terminal. Final history, timestamps, documents, task index and event IDs are preserved. Content fingerprints, exact ownership paths, completed status and a valid process pin are checked before replay. Journal payload uses JSON (valid YAML) to preserve multiline strings. Successful replay removes the intent after mandatory writes/events.

Public files: `src/processforge_core/process_execution.py`; two new smokes `tools/smoke_work_evidence_freshness.py` and `tools/smoke_work_completion_recovery.py`; two registrations in `tools/processforge.py`; `checksums/processforge.sha256`.

## Actual validation

| Evidence | Result |
| --- | --- |
| `baseline-reproduction.json` | Original F03/F04/F05 reproduced in real temporary PF project |
| `f0304-final.json` | Evidence matrix PASS, 199.245s |
| `f0304-final-isolated-results.json` | Public-copy PASS 207.276s; baseline F03 and independent F04 controls FAIL as expected |
| `final-evidence.json` | Combined-source evidence matrix PASS, 278.620s |
| `f05-matrix-2.json` | 18 before/after failure points and invalid journal cases PASS, 202.979s |
| `final-public-results.json` | Final F05 public-copy PASS, 216.367s; baseline FAIL on done/in_progress terminal retry, 38.141s |
| `related-results.json` | Ten existing transition/process checks PASS |
| `final-terminal.json`, `final-events.json` | After final journal encoding change: existing terminal/event smokes PASS |
| `source-preservation.json` | Unrelated tracked bytes and previous public inventory preserved; CLI differs only by two registrations |
| `checksum-final.txt` | Public inventory matches |

Recovery tests cover writes of intent, assignment, run, summary, handoff, index, projection, event, and journal cleanup, before and after each. They use fresh service instances, explicit/default selection and `complete()`, mutate evidence after committed intent, check one final history entry, original timestamps, exact document content and unique event IDs. Structural corruption tests recompute fingerprints for invalid ownership/status/pin cases and still require refusal without writes.

## Orchestration and rejected attempts

Four PF codex-exec shell assignments use `gpt-5.6-luna`: F03/F04, sequential F05, independent assurance, then final review. Source ownership transfers explicitly; primary owns integration and real acceptance tests. Worker sandbox TemporaryDirectory WinError 5 was reported, not worked around or counted as PASS.

Primary corrected worker test fixtures (pinned definition, missing file, Forge-only `can_complete` route), replaced incomplete F05 smoke with the complete matrix, and repaired two issues found by that matrix: a corrupted cancelled run payload accepted as completion, and YAML folding that invalidated journal fingerprints. Original worker files and failed attempts are preserved. `f05-matrix-final` and `f05-isolated-final` names refer to rejected intermediate attempts; `f05-matrix-2` and `final-public` are their accepted successors.

## Boundaries and next work

F06-F12 remain open. Full source release qualification remains blocked by the separately reproduced baseline Runtime startup failure recorded in the F01/F02 handoff. This batch did not rerun the entire known-failing release suite or qualify an archive/extracted release candidate.

File checks retain the normal filesystem TOCTOU window. Completion is recoverable across multiple files, not an atomic read snapshot for concurrent readers. Durable events deduplicate by ID; hook delivery may repeat. No exactly-once hook guarantee is claimed.

## Independent acceptance

Both `f0305-assurance/report.md` and `f0305-review/report.md` give bounded PASS. Four worker assignments are collected DONE. Final schema and public-cleanliness checks pass. Shell and carrier run doctors pass. See closeout.json for terminal lifecycle confirmation.
