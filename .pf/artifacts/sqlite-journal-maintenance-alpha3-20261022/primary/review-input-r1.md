# Independent native review input: alpha3 maintenance

Implementation and scoped primary QA are complete. Review the primary plus all
four native contributions in the canonical candidate tree named by
source-candidate-r2.json. For each manifest path, open candidate/path; never review
the unrelated dirty Main or paused OOP54-55 files in the outer working tree.
Verify the manifest's actual hashes before and after reading. Read main-owned.diff
and legacy-before.private.py to compare the actual Main delta and legacy behavior.

Read the frozen architecture, file-only handoff, actual Python source excerpts
and provenance, guidance and selected current OOP architecture rules. Read the
actual test-report-r1.md, code-quality-report-r1.md and receipt/coverage manifests.
No external knowledge/QA tool grant is needed: actual material and results are
project-local inputs. Use scoped file reads and optional stdlib checks only.
Do not invoke Git, PF lifecycle, external QA, infrastructure, package installation
or another agent. Primary owns those operations and final release delivery.

Independently review every owned production file, Main registration, tests and
EN/RU docs. Focus on consistency under WAL/concurrent commits, corrupt byte
preservation and provenance, explicit refusal/skip/counters, source drift and
identity conflicts, safe file/member paths including reparse points, no overwrite
or source rewrite, failure cleanup/barriers/retry, verified record replay,
constructor/import boundaries, bounded waits and preservation of released CLI
flags/output/exit behavior. Assess test strength rather than mirrored structure.
Two-database finalization has separate commits; hard process death between them
needs operator evidence inspection and explicit retry. Do not claim global atomicity.

Report actual defects with severity, canonical path/line, concrete trigger and
required correction. Separate must-fix defects from optional follow-ups and known
documented scope limits. State CODE GO or NO-GO. Public source/archive qualification
is pending and must not be reported as complete. Do not implement product fixes
or review your own code. Emit real READ_ACK after reading, then a complete RESULT
report for primary, without claiming the parent/release done. Keep source hashes
stable throughout this review; no product writer runs concurrently.
