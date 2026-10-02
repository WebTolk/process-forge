# E01/E02 assurance

Verdict: **pass_with_conditions for the bounded Windows source batch**. No remaining defect was found in the changed scope. This is not full release, archive, installed Core, actual MCP host or native-client acceptance. Review performed sequentially by the primary agent under the pinned single-agent process; no independent reviewer claim.

## Review and test plan

Reviewed canonical ownership separately from client delivery, instruction accounting separately from model tokens, and local Work creation scope separately from immutable reuse. Exercised negative cases before positive migration, exact byte preservation, stale source/target/config input, actual filesystem redirects and ACLs, interruption at each write boundary, late edits, process termination and lock contention. Public source hash inventory is source-hashes.json; protected-input evidence is preservation.json.

Semantic review of K covered all eight clauses: manifest/context/freshness; blocking context conditions; returned Work identity and explicit process choice; capsule identity/empty grants; authorized resource resolution; pinned stages and standard transitions; one writer, immutability, scratch and privacy; infrastructure prohibition and advisory handoffs. The exact reviewed draft was retained. No pointer-only projection or technical-enforcement claim was introduced.

## Results

| Check | Result | Evidence / boundary |
|---|---|---|
| AT01/AT02 source, metadata, clauses, size, normalized blocks, renderer | PASS | commands/entry-final.json; exact 4096 boundary, source BOM/CRLF/byte/version corruption and pointer-only derivative negatives |
| AT04/AT05 bytes and ownership | PASS | UTF-8/BOM/CRLF, absent newline, unchanged user prefix/suffix, known hidden legacy suffix; malformed/duplicate/edited/unknown blocks and unknown manifest schema refuse writes |
| AT06 preconditions and Windows paths | PASS, Windows scope | Source/target/selected input changes; real hard link, case collision, junction and post-staging path replacement; direct traversal/absolute/ADS/control-character rejection. Junction exercises the Windows reparse boundary; no native symlink-creation qualification or POSIX claim |
| AT07/AT08 interruption and recovery | PASS | Faults after staging, data replacement, projection replacement and manifest replacement; incomplete journals never mean committed; rollback preserves exact bytes, refuses late edits and validates journal schema |
| AT07 process death / writer ownership | PASS | Actual child exit between data replacement and ACL restoration, actual competing process lock, killed lock owner and successful reacquisition |
| R13 source accounting | PASS, generic policy only | Whole file and ordered chain, duplicate selection, unselected K, exact/zero limits, Unicode scalar vs UTF-8 vs UTF-16, K fitting with required tail lost, warning-only policy, token/default/unknown unverified, late selected input change |
| AT19 read-only/public/privacy/preservation | PASS, bounded source scope | CLI plan/check leave bytes/mtime unchanged and create no files; explicit apply required; public plan omits user text and absolute paths; 6949 baseline files checked, only six authorized existing product files changed |
| Scoped native Work creation repair | PASS | commands/smoke_work_start_scope-final.json: defaults remain empty, invalid intent publishes no Run/Task/capsule, same intent reuses, changed intent refuses, explicit predecessor transfer still rejects a third writer, native transition succeeds with unchanged capsule |
| Capsule contract parity | PASS | commands/bootstrap-capsule-parity.json; supported scope/identity and immutability negatives. Host could not create symlink fixture; recorded skip |
| Work resource binding | PASS | Completed exec session 49642: isolation, pinning, current access, metadata/fulltext/subsets/provenance; symlink fixture unsupported on host |
| Existing startup/infrastructure instructions | PASS | commands/smoke_docs_agent_no_manual_infra-final.json and smoke_software_lifecycle_prompt_alignment-final.json |
| Public-tree schema validation | PASS | commands/public-tree-schemas.json; isolated copy of current public source, not a release/archive qualification |
| Checksums / public cleanliness / syntax / diff | PASS | commands/source-checksums.json, privacy-final.json, diff-check.json; AST parse in preservation.json |
| Full live-workspace schemas | FAIL, unrelated runtime data | commands/live-schemas.json: existing zero-byte `.pf/runtime/hooks/outbox/wtaicc/evt_347237f8918c45afa5505fcbee6525ac.wtaicc-outbox.json`; no Runtime repair authorized or performed |
| Existing process execution integrity smoke | FAIL on candidate and pristine HEAD | commands/bootstrap-integrity.json and baseline-integrity.json: expects `process_pin_invalid`, actually receives the earlier `work_context_mismatch` refusal; identical at fb3527e4, not introduced here |

## Resolved implementation findings

1. Windows replacement re-inherited ACLs on this filesystem despite the expected API merge behavior. The implementation now preflights the filesystem on empty private files with the target-parent ACL, captures the expected intermediate state, and restores/verifies the original owner/group/DACL. Recovery handles death between the data and metadata steps. Unsupported preservation fails; no ignore-ACL option is used.
2. A selected budget input could change after staging. Input and source checks now run before target writes and again before commit; tests preserve the late edit and refuse migration.
3. Post-staging target replacement is rechecked immediately before writes. A hard-link substitution test confirms no write to the outside target.
4. Recovery checks permissions as well as content; a rollback interrupted after restoring data still restores the expected ACL before recording completion.
5. Malformed legacy coordination values now fail closed in the scope-transfer helper. No malformed prior identity is interpreted as a valid handoff.

## Explicit applicability

Browser verification: `status: not_applicable`; reason: CLI, file contracts and local filesystem operations only, no UI change; evidence: implementation-report.md and source-hashes.json.

Release/archive/install/host/native-client qualification: `status: not_applicable` to E01/E02; reason: staged plan assigns these to E09/E10/E11 and separate client integrations. Tests do not raise previous evidence levels. POSIX is `not_run`, Windows is the executed filesystem platform. Actual-project entry migration is `not_run`; root AGENTS remains absent and current hidden instructions/START/snapshot/capsules remain preserved.

The two full-workspace/baseline failures remain explicit conditions for any broader release gate. They do not invalidate the demonstrated source behavior, and are not silently treated as passing. Source delivery may proceed within this batch; release readiness remains deferred.
