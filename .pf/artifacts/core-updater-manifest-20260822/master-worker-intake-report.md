# Master Worker Intake Report

## Scope Status

Assignment: `core-updater-manifest-master-intake-20260822`
Run: `core-updater-manifest-20260822`
Mode: planning only; product code changes are not allowed.

Sources used within scope:

- `.pf/AGENTS.md`
- `.pf/process-forge.yaml`
- `.pf/contexts/project-context.snapshot.yaml`
- `задания/process-forge-core-updater-manifest-master-prompt.md`
- embedded assignment capsule from the launch prompt

The assignment file itself was not read from disk because it is not listed in `allowed_read_files`; the embedded capsule contains the effective assignment fields and was sufficient for this intake.

No product files under `tools/**`, `src/**`, `schemas/**`, or `docs/**` were read or edited.

## Intake Conclusion

The requested work should be decomposed as a governed in-place core updater initiative. The core invariant is that the installed core manifest defines PF-owned file ownership, and update deletion must be limited to paths present in the old manifest and absent from the new manifest.

Recommended orchestration shape:

1. Audit the current install/update/release surfaces.
2. Design the core manifest and archive manifest contract.
3. Design the update transaction, recovery, local modification, and Windows locking model.
4. Implement read-only manifest validation and planning first.
5. Implement explicit apply/repair only after the plan path is verified.
6. Integrate release archive generation and clean install/update parity.
7. Run smoke tests, independent review, and final validation.

## Task Graph

| Task | Purpose | Depends On | Primary Output | Product Writes |
| --- | --- | --- | --- | --- |
| `core-updater-current-state-audit` | Locate existing install/update/release code, current archive shape, CLI conventions, Runtime/MCP startup checks, and existing tests. | none | `core-updater-current-state-audit.md` | none |
| `core-manifest-design` | Define installed core manifest and release manifest schema, path rules, hashing, ownership semantics, and directory handling. | audit | `core-manifest-design.md` | none |
| `core-update-transaction-design` | Define plan/apply/finalize/repair transaction, staging, backup/journal, locally modified handling, and Windows locked-file behavior. | audit, manifest design | `core-update-transaction-design.md` | none |
| `core-updater-plan-slice` | Implement or adapt read-only `status` and `plan`: archive validation, manifest validation, add/change/remove diff, local modification detection, and non-destructive diagnostics. | designs | `core-updater-implementation-report.md` partial | yes |
| `core-updater-apply-repair-slice` | Implement explicit `apply` and `repair`: staged replacement, backup/journal, manifest-last finalize, incomplete update detection. | plan slice | `core-updater-implementation-report.md` | yes |
| `core-updater-release-integration` | Ensure release archive includes full manifest/checksums and supports both clean install and update. | manifest design, plan slice | implementation report update | yes |
| `core-updater-runtime-mcp-slice` | Add or wire owned Runtime/MCP preflight, optional stop/start, and health checks without unsafe PID-only termination. | transaction design, apply slice | implementation report update | yes |
| `core-updater-tests-smokes` | Add required unit/integration/smoke coverage for add/change/remove, unknown files, local changes, crash, malicious paths, locked files, clean install, Runtime/MCP. | implementation slices | `core-updater-smoke-report.md` | test writes |
| `core-updater-independent-review` | Independent review against the prompt invariants. | implementation and smoke | `independent-code-review.md` | none |
| `core-updater-final-validation` | Run final quality gates and summarize release readiness. | review | `final-validation.md` | none |

## Write Scopes

Current worker write scope:

- `.pf/artifacts/core-updater-manifest-20260822/master-worker-intake-report.md`

Future task write scopes should be assigned with one writer per file scope:

| Task | Artifact Write Scope | Product/Test Write Scope |
| --- | --- | --- |
| Audit | `.pf/artifacts/core-updater-manifest-20260822/core-updater-current-state-audit.md` | none |
| Manifest design | `.pf/artifacts/core-updater-manifest-20260822/core-manifest-design.md` | none |
| Transaction design | `.pf/artifacts/core-updater-manifest-20260822/core-update-transaction-design.md` | none |
| Plan slice | `.pf/artifacts/core-updater-manifest-20260822/core-updater-implementation-report.md` | exact files to be named by audit; expected areas are CLI/updater/release validation code and manifest schema surfaces |
| Apply/repair slice | same implementation report | exact updater transaction files named by audit |
| Release integration | same implementation report | exact release packaging/docs files named by audit |
| Runtime/MCP slice | same implementation report | exact runtime/MCP integration files named by audit |
| Tests/smokes | `.pf/artifacts/core-updater-manifest-20260822/core-updater-smoke-report.md` | exact test files named by audit |
| Independent review | `.pf/artifacts/core-updater-manifest-20260822/independent-code-review.md` | none |
| Final validation | `.pf/artifacts/core-updater-manifest-20260822/final-validation.md` | none |

Do not assign product write scopes until the audit has identified concrete files. This avoids overlap and prevents premature edits in unknown modules.

## Artifact Map

Required final artifact set from the master prompt:

- `core-updater-current-state-audit.md`
- `core-manifest-design.md`
- `core-update-transaction-design.md`
- `core-updater-implementation-report.md`
- `core-updater-smoke-report.md`
- `independent-code-review.md`
- `final-validation.md`

Recommended statuses:

| Artifact | Initial Owner | Target Status |
| --- | --- | --- |
| `master-worker-intake-report.md` | intake worker | ready_for_review |
| `core-updater-current-state-audit.md` | audit worker | ready_for_review |
| `core-manifest-design.md` | design worker | ready_for_review |
| `core-update-transaction-design.md` | design worker | ready_for_review |
| `core-updater-implementation-report.md` | implementation owner | ready_for_review |
| `core-updater-smoke-report.md` | test owner | ready_for_review |
| `independent-code-review.md` | reviewer | ready_for_review |
| `final-validation.md` | orchestrator/validator | ready_for_review |

## Quality Gates

Minimum gates before implementation:

- Current-state audit identifies exact code paths for install/update/release/CLI/tests.
- Manifest design defines `schema_version`, `version`, `commit/build`, file entries, SHA-256, and relative-path-only containment.
- Transaction design defines staging, backup/recovery journal, incomplete status, repair path, and manifest-last finalize.

Plan/read-only gates:

- Reject manifest paths with `../`, absolute paths, or resolved paths outside core root.
- Verify every declared archive file exists.
- Verify SHA-256 for every declared file.
- Compute `removed`, `added`, and `common` strictly from old and new manifests.
- Detect `locally_modified` by comparing current file hash with the old manifest.
- `plan` is read-only and produces no product changes.

Apply gates:

- Delete only paths present in old manifest and absent from new manifest.
- Preserve unknown files.
- Do not recursively delete directories containing unknown/user files.
- Do not silently overwrite locally modified core files.
- Use explicit policy for local changes: abort/warn, backup, or explicit force.
- Write the new manifest only after successful apply.
- Locked file on Windows must block clearly and must not result in success.
- `status` and `repair` must detect an interrupted update.

Release/installation gates:

- Release archive contains the full new manifest.
- One archive supports clean install and update.
- Clean install is modeled as absent old manifest plus archive validation.
- Derived data such as SQLite indexes and caches are excluded from the core manifest.
- Required maintenance for derived data runs separately after update.

Runtime/MCP gates:

- Preflight identifies PF Runtime, MCP server, and other owned PF processes using ownership verification.
- Stop/start happens only when required.
- Post-update checks include Runtime start/health, MCP initialize, and MCP tools/list.

Final gates:

- `bin/pf.py --help`
- Runtime start/health
- MCP initialize
- MCP tools/list
- critical smokes
- release/archive validation
- EN/RU docs updated
- independent review PASS
- `git diff --check` PASS

## Blockers And Risks

- The snapshot health is `blocked`, and the resolved context reports missing `research` and `process_governance` capabilities for `knowledge-package-improvement`. The current planning assignment can proceed because its effective required capabilities are empty, but the full run should refresh or adjust the resource profile before implementation governance.
- Current scope forbids reading `tools/**`, `src/**`, `schemas/**`, and `docs/**`; therefore exact implementation files, commands, existing conventions, and test locations are not confirmed in this intake.
- `workspace_access` provides no knowledge resources, templates, tools, or MCP access. Future workers needing docs/tools must receive explicit access.
- Windows locking behavior is a first-class risk and needs a dedicated test path, not just general file replacement tests.
- Runtime/MCP process ownership must be verified before stop/kill actions; PID-only handling is explicitly unsafe.
- Release integration can regress clean install if update and install diverge; keep them as one manifest-based model.

## Recommended First Implementation Slice

Do not start with destructive `apply`.

Recommended first slice:

1. Complete `core-updater-current-state-audit.md`.
2. Complete `core-manifest-design.md`.
3. Implement the read-only manifest validation and `plan` path.
4. Add focused tests for:
   - valid archive manifest;
   - malicious paths;
   - checksum mismatch;
   - old/new diff;
   - unknown file preservation in planned deletion;
   - locally modified detection.
5. Produce a plan artifact/report showing add/change/remove and blockers without modifying the core directory.

This slice proves the ownership model and safety checks before any file replacement, deletion, recovery, Runtime/MCP, or release mutation is introduced.
