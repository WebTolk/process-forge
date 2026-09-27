# T03 regression writer report

## 2026-09-26 03:36 UTC - regression writer

Task: Add and run the focused T03 capsule parity and immutable intent smoke.

Files changed:
- `tools/smoke_work_capsule_contract_parity.py`
- `.pf/artifacts/t03-unified-context-20260926/worker-regression.md`

Artifacts changed: This report only.

Templates used: None.

Tools used: Focused reads of the accepted T03 domain/architecture, `developer-probe.py` and output, common work-context code, and process execution fixture/service. Ran only `python tools/smoke_work_capsule_contract_parity.py` for behavioral verification.

Decisions: Both constructors run against isolated project clones. Synthetic tasks are persisted as exact members of the fixture Run before capsule creation. The smoke leaves the fixture's active capsule alone until the separate governed transition check. It covers empty permissions/resources, analysis write denial, explicit worker capability/source blockers, source/path budgets and symlink containment, intent stability/mutations, outer capsule byte anchoring, required source conflicts, run identity, legacy/version handling, force refusal, pinned process/stage parameters, and capsule immutability through a real transition.

Run history:
- Initial setup attempt failed because putting a missing process capability in the fixture definition made the project-context refresh helper return nonzero after reporting a fresh snapshot. Adjusted the test to inject the lifecycle capability only into an isolated pin.
- Next attempt failed in smoke setup because the test imported `canonical_fingerprint` from the CLI adapter module; corrected the import to the process execution module.
- Next attempt reached legacy validation, which correctly returned `status: legacy`; adjusted the assertion to accept that status when the reason is `legacy_contract_incomplete`.
- A pre-fix smoke run then passed its narrower checks. It was superseded by primary's run-membership, intent-obligation, duplicate-checksum and outer-byte-anchor fixes and was not treated as final.
- Final targeted run after those fixes: `PASS` (exit code 0). It reported 17 named checks passing. Symlink containment was skipped because the host rejected symlink creation with `OSError`; traversal and absolute paths were still checked.

Checks: Final smoke verified exact execution-contract equality from both actual capsule constructors. It also checked `input_artifacts` and `completion_criteria` mutations, a forged inner source hash with a recomputed contract checksum against a governed outer byte pin, a missing and non-member Run, duplicate conflicting source checksums, required input mutation/deletion, malformed execution mode/subagent policy, and lifecycle/preference changes. Both owned files have no trailing whitespace. `git diff --check` emitted no diagnostics for the owned paths.

Risks: Host symlink behavior could not be exercised on this machine. Installed Core/real-host acceptance remains outside this local smoke.

Next steps: Primary integration can incorporate the smoke and record its path in the release-test registry and checksum inventory under the authorized T03 scope.

Handoff: The test is ready for primary review. No product code, schema, documentation, existing tests or checksum inventory was changed by this writer.
