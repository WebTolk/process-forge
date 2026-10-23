# Fresh independent final review of r15

Review only source-candidate-r15.json's candidate-r14 tree, all 41 exact files;
verify hashes before/after. Main delta: main-owned-r4.diff. The previous r13 tree
at candidate-batch remains unchanged, as do r4 and r10. Read review-final/report.md
and its exact stdlib probes/results: that completed review is CODE NO-GO, never GO.
Read review-corrections-plan-r4 and all prior r2-r10 decisions/Python/OOP guidance
listed in review-input-r3. Review actual corrected code rather than old conclusions.

Independently verify all four newest findings: strict collection cannot silently
omit unavailable/missing roots or drop cached rows; a source verification error
cannot delete the established DB; canonical root-set fingerprint catches unselected
empty-root remaps/additions; the actual Main lifecycle wrapper guards the whole
observation-plus-coverage read. Intentional containment refusals remain exclusions,
using the existing resolver authority, while missing/permission failures fail
closed. That lazy resolver API must be modeled correctly in isolated fixture stubs.
Explicit rebuild collects before old-cache removal and reuses captured material;
the previous documented replacement contract otherwise remains, no atomic DB-swap
claim. Inspect error/privacy/public-contract and metadata/cache-compatibility edges.

Recheck earlier original findings plus batch sequencing/native transaction and
audit semantics, apply/default/dry-run, duplicate/partial/index failures, exactly
one successful qualified-ID selection, notifications under concurrency/failure,
older global failure/unknown changes, physical/project/work authorization/counts,
metadata-only/no URL fetch, root/policy/disabled-row behavior and hidden hash removal.
The exact bundled schema ref is allowed; unrelated external refs remain rejected.

Read test-report-r4, quality, coverage/QA receipts and actual CLI acceptance r4.
Current source has a fresh full pytest/native/static pass, not an AST-only reuse.
Retained SQLite warnings are not claimed fixed. The full source/archive release
gates remain pending; installed/connected-host/POSIX acceptance is not asserted.
Current store is SQLite FTS5, actual backend Protocol is narrow and tested. CLI
and cold future scheduler use one owner; there is no real periodic job or new DB.

Emit actual READ_ACK. Write only your review artifacts/log/scratch; no product,
Git, lifecycle, live workplace/indexing, infrastructure, external QA or subagents.
Stdlib probes on own fixtures are allowed. State each concrete defect with
severity/path/line/trigger/impact/correction and final CODE GO or NO-GO plus RESULT.
Primary owns changes, registered QA, full release gates and delivery.
