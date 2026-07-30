# Review: failure-atomic authoring transaction slice

- Review id: `pre-release-remediation-transaction-review-20260730`
- Date: 2026-07-30
- Assignment: `remediation-transaction-review-20260730`
- Run: `pre-release-remediation-20260730`
- Reviewer: `codex-remediation-transaction-reviewer`
- Session: `pre-release-remediation-20260730-transaction-review`
- Lease: `lease-remediation-transaction-review-20260730`
- Product state: frozen; no product files changed
- Result: **FAIL**

## Decision

The frozen transaction slice is not acceptable for release. It substantially
improves ordinary preflight and rollback, but it does not close PF-AUD-010 and
does not implement the accepted crash-recovery or post-commit replay contract.

Three release-blocking defects were reproduced independently:

1. Platform authoring publishes `status: available` and emits fabricated
   `platform.contract.doctor.passed`/`platform.authoring.completed` without
   running the platform doctor or an equivalent staged semantic validator.
2. Crash recovery may mark a transaction `rolled_back` while leaving created
   authoritative directories or restoring bytes whose SHA-256 differs from the
   recorded pre-image.
3. Post-commit retry reruns already completed effects, has no public/automatic
   replay path, and remains `committed_audit_pending` even after a manual retry
   completes all effects.

The strict pre-release contract is also still advertised and accepted through
deprecated parser aliases. The implementation therefore cannot be approved by
waiving only a missing test.

## Finding disposition

| Finding | Result | Evidence |
|---|---|---|
| PF-AUD-010 | **FAIL / open** | Schema-valid but semantically invalid platform was committed as `available`; later doctor failed, while passed/completed events already existed |
| PF-AUD-011 | **PASS for original parent/injected failures; transaction assurance FAIL** | Manifest/index/private registry restore exactly on tested in-process failures, but common crash recovery does not prove exact restoration |
| PF-AUD-019 | **PASS for canonical layout; strict surface FAIL** | Create/install use canonical path and legacy state is rejected; no migration command exists, but deprecated platform input aliases remain public and accepted |
| PF-AUD-020 process-create slice | **PASS for original partial-state cases; parity condition FAIL** | Uninitialized root writes nothing and dry-run lists 16 files plus effects; dry-run does not execute common preflight and can return success for a plan that apply rejects |

## Source inspection

Serena was used first. Project onboarding was available, but Python symbol
extraction failed with `Active languages: []`. Serena pattern search and bounded
line reads were then used as the documented fallback.

### Common transaction path

Reviewed symbols in `tools/processforge.py`:

- `AuthoringWrite`, `AuthoringEffect`, `AuthoringPlan` (`402-430`);
- `authoring_mode` (`442-449`);
- `preflight_authoring_plan` (`507-529`);
- `render_authoring_plan` (`532-549`);
- `stage_authoring_plan` (`552-592`);
- `validate_staged_authoring_plan` (`595-609`);
- `publish_authoring_write` (`623-646`);
- `rollback_authoring_plan` (`649-684`);
- `commit_authoring_plan` (`687-722`);
- `run_post_commit_effects` (`725-738`);
- `execute_authoring_plan` (`741-752`);
- `recover_authoring_transaction` (`755-778`);
- `planned_registry_upsert` (`781-809`).

Correct ordering exists in normal execution:

```text
preflight
-> journal/staging
-> staged validation
-> entity writes
-> registry writes
-> committed
-> post-commit effects
```

`planned_registry_upsert` rejects invalid YAML and non-list collections without
replacing the original registry. `authoring_mode` enforces XOR before plan
construction in the affected one-shot handlers.

However:

- `rollback_authoring_plan` treats lack of `OSError` as verification; it never
  compares restored bytes with `pre_sha256`;
- `recover_authoring_transaction` neither verifies pre-image hashes nor removes
  `created_directories`;
- `run_post_commit_effects` resets its local completed list, ignores the
  journal's prior successes and never transitions a successful replay out of
  `committed_audit_pending`;
- `incomplete_authoring_journals` counts `committed_audit_pending` as terminal;
- no CLI handler invokes `recover_authoring_transaction` or rehydrates
  post-commit effects.

### Platform wiring

`build_platform_authoring_plan` (`22255-22444`) builds entity and registry
writes correctly with registries last. But the plan is created with:

```text
validation_callbacks=[]
```

Its one post-commit callback unconditionally emits:

```text
platform.contract.doctor.passed
platform.authoring.completed
```

Neither `command_platform_create` (`22447-22456`) nor
`command_platform_contract_install` (`22503-22516`) calls
`command_platform_contract_doctor` or shared staged doctor logic.

By contrast, the public doctor (`21090-21251`) checks missing required parent
platforms, inheritance cycles, required packages/templates and resolved stack
semantics. These checks are absent from the authoring transaction.

### Knowledge wiring

`build_knowledge_resource_add_plan` (`20637-20808`) renders package manifest and
resource index from one in-memory object. A private path creates a planned
registry-last write. Both documents are schema-validated before publication.

The source inspection and independent probes confirm that the original
manifest-before-index failure and hidden private registry mutation are fixed for
ordinary/injected in-process failures.

### Process wiring

`build_process_create_plan` (`12589-12760`) calls `require_flow_root` first,
renders six session files, three primary public files and seven examples, and
declares six event effects plus twelve conditional hook patterns. It shares the
planner with `command_process_authoring_apply`.

The plan has a staged process validation callback. However, command dry-run
paths call only `render_authoring_plan`; they do not call the pure common
`preflight_authoring_plan`. This permits false-green dry-runs for invalid parent
types/collisions.

## Strict mode and legacy rejection

### PASS

An independent fingerprint probe exercised all six affected commands:

```text
knowledge-add-url: neither=2 both=2 no_write=True
knowledge-add-resource: neither=2 both=2 no_write=True
platform-create: neither=2 both=2 no_write=True
platform-contract-install: neither=2 both=2 no_write=True
process-create: neither=2 both=2 no_write=True
process-authoring-apply: neither=2 both=2 no_write=True
```

The parser contains no `platform-contract-migrate` command. Dedicated legacy
fixtures confirmed that legacy-only and canonical-plus-legacy states fail
without mutation.

### FAIL

The public parser still declares and implementation still consumes:

- `platform-create --package`;
- `--knowledge-package`;
- `--template`;
- `--tool`;
- `--mcp`;
- `process-authoring-apply --id` as a “Compatibility alias”.

An external probe passed `platform-create --package docs.legacy --dry-run` and
received exit `0` with no writes. This violates the accepted no-compatibility
ADR, which requires removal rather than warning/help text.

Knowledge and platform `--dry-run` help also still says “Write proposal only”,
although pure dry-run writes no proposal.

## Failure injection and mutation fingerprints

All fingerprints included files and directories, exact file SHA-256, registry
bytes, ordinary events, proposals/reports and hook trees. Transaction journal
subtrees were excluded only where the ADR explicitly permits an audit-only
failure journal.

### Knowledge: PASS

Independent injections were run after:

```text
after_entity_publish:1
after_entity_publish:2
after_registry_publish:1
```

The last case included a newly planned
`registries/private-resource-paths.yaml`. Every injection returned failure and
the complete non-journal workplace tree was identical to its pre-operation
fingerprint:

```text
after_entity_publish:1: exact_tree=True
after_entity_publish:2: exact_tree=True
after_registry_publish:1: exact_tree=True
```

A regular-file collision at the knowledge index parent also failed without
changing manifest, index, private registry or audit state.

### Platform semantic failure: FAIL

The test-only source injector added this schema-valid semantic requirement to a
generated platform contract:

```yaml
requires:
  platforms:
    - id: platform.missing-parent
      required: true
```

Observed result:

```text
create_rc=0
registry_status=available
doctor_rc=1
doctor_passed_event=True
completed_event=True
doctor_detected_missing_parent=True
```

The command committed a platform that the public doctor immediately rejected.
This exactly reproduces PF-AUD-010 under the new implementation.

## Process-create evidence

### PASS

On an uninitialized project:

```text
returncode=1
fingerprint unchanged=True
.pf absent=True
```

On an initialized project, dry-run was write-free and printed:

```text
entity rows=16
audit event rows=6
conditional hook rows=12
all seven example files present=True
```

The dedicated injected failure after the fourth entity also restored the
project fingerprint.

### FAIL: common preflight is bypassed by dry-run

With `indexes` replaced by a regular file:

```text
knowledge-add-resource --dry-run: returncode=0
knowledge-add-resource --apply: returncode=1
both paths write-free=True
```

Dry-run printed the impossible `indexes/resource-index.yaml` destination but
did not run `validate_authoring_parent_types`. The same handler structure is
used by platform and process dry-runs. Logical destination completeness is
fixed, but pure preflight/apply feasibility parity is not.

## Journal recovery: FAIL

### Blocking behavior

A subprocess was terminated with `os._exit(93)` after the first entity
publication. The preparing/prepared journal correctly blocked the next
mutation. Calling `recover_authoring_transaction` changed it to `rolled_back`
and unblocked mutation.

### Created-directory leak

The crashed transaction had created:

```text
authoritative/deep/created.txt
```

Recovery removed the file but left:

```text
authoritative/
authoritative/deep/
```

It still returned `rolled_back`.

### False verified rollback

A second crash replaced an existing file. Before recovery, the journal backup
was deliberately corrupted. Recovery returned:

```text
recovery_state=rolled_back
original_restored=False
expected_pre_sha=25718360e05d3c2d0963d1381e9dd4dae5fca789244ee4b9f861adcc0cc96218
actual_sha=3773107ff4c96d096e76614cebfb9b99b0ca706340854b29f293e573a4950ae9
```

The recovery path did not compare the result to `pre_sha256`. It may therefore
silently certify corrupted authoritative state.

## Post-commit effects: FAIL

An `AuthoringPlan` with two post-commit effects was executed. Effect one
succeeded; effect two raised.

First attempt:

```text
state=committed_audit_pending
post_commit_completed=[one]
effect_one_count=1
```

After replacing effect two with a successful callback and invoking the only
available internal runner again:

```text
state=committed_audit_pending
post_commit_completed=[one, two]
effect_one_count=2
effect_two_count=1
```

The completed first effect was duplicated, and the journal never became audit
complete. `process_authoring_event_effect` also uses
`process-authoring-<process-id>` correlation rather than a transaction/effect
id; its callback creates a new event id on each invocation. The required
exactly-once/idempotent replay is not present.

## Minimal implementable correction

### 1. Shared staged platform checks

Extract a pure `platform_contract_checks_from_view` used by both the public
doctor and a `validate_platform_plan` callback. The callback receives staged
contract bytes and proposed registries, resolves parent/resource dependencies
against that virtual view, and must pass before registry publication. Remove
literal doctor-passed/completed emission from any path that did not run it.

### 2. Recovery verification

`rollback_authoring_plan` and `recover_authoring_transaction` must:

1. restore/remove destinations in reverse order;
2. remove `created_directories` in reverse order when empty;
3. verify every existing restored file equals `pre_sha256`;
4. verify every pre-missing destination is absent;
5. keep backups until all checks pass;
6. set `rolled_back` only after proof; otherwise set `recovery_required` and
   keep mutation blocked.

Recovery must validate journal shape, destination containment and transaction
root before touching paths.

### 3. Durable post-commit replay

Callbacks cannot be recovered from YAML. The journal must persist enough
deterministic effect data to rehydrate the effect plan:

- stable `effect_id` derived from transaction id plus ordered effect kind;
- effect kind, destination/sink, event/report/proposal payload and idempotency
  key;
- per-effect state `pending|running|succeeded|failed`, attempts and last error;
- a versioned command-specific rehydration key/payload.

Before invoking an effect, persist `running`; after it succeeds, persist
`succeeded`. Replay skips `succeeded` effects and resumes only pending/failed
ones. External event/hook sinks must accept the stable effect id as their
event/delivery idempotency key, covering a crash after side effect but before
the success journal write.

Add a public or automatic recovery path, for example:

```text
authoring-transaction-recover \
  --runtime-root <runtime-root> \
  --transaction <id> \
  --apply
```

It selects behavior by journal state:

- pre-commit incomplete: verified rollback or verified commit completion;
- `committed`/`committed_audit_pending`: rehydrate and replay unfinished
  effects only;
- `recovery_required`: retry verified recovery, never silently unblock.

Terminal states are only:

```text
rolled_back
committed_audit_complete
```

`preparing`, `prepared`, `committing`, `committed`,
`committed_audit_pending` and `recovery_required` are non-terminal for health
and recovery. `committed_audit_pending` may retain authoritative state, but it
must not be treated as completed and must fail the relevant doctor/release
gate. Successful replay moves it to `committed_audit_complete`.

### 4. Dry-run and strict parser

Every dry-run handler calls pure `preflight_authoring_plan(plan)` before
rendering. Remove deprecated platform aliases and process apply `--id`; update
help to say “Show complete plan without writing.”

## Regression tests

Executed and passed:

```text
python tools/smoke_remediation_transactional_authoring.py
python tools/smoke_remediation_platform_layout_strict.py
python tools/smoke_remediation_process_create_transaction.py
python tools/smoke_platform_create_include_levels.py
python tools/smoke_process_authoring_writes_user_root.py
python tools/smoke_process_authoring_materializes_evolve.py
python tools/smoke_process_authoring_materialization_parity.py
python tools/smoke_process_authoring_evolve_targeting.py
python tools/smoke_process_authoring_evolve_questions.py
python tools/smoke_process_definition_schema_contract.py
python tools/validate-process-forge-schemas.py
```

The three dedicated smokes pass because they do not cover the confirmed
failure surfaces:

- platform smoke injects only after entity publish, not staged doctor failure;
- recovery after process death, directory cleanup and backup hash corruption
  are absent;
- post-commit effect failure/replay is absent;
- process smoke checks selected path strings rather than exact 16/6/12 rows;
- all-six-command XOR is not covered in one matrix;
- dry-run never faces a common-preflight failure.

Required additions:

1. semantic platform doctor failure with registry/event fingerprint;
2. subprocess crash recovery including created directories and corrupted
   backup;
3. two-effect failure/replay proving no duplicate and terminal audit-complete;
4. exact all-six XOR;
5. exact 16/6/12 process dry-run;
6. dry-run/apply preflight parity;
7. parser rejection of every removed legacy alias.

## Residual risks

- The journal itself has no shipped JSON Schema in the reviewed slice.
- Per-file `os.replace` gives failure atomicity only when recovery is correct;
  the current false-verified recovery is therefore a core safety defect.
- Proposal/report/event callbacks combine several writes into one effect. Even
  after effect-level replay is fixed, their sinks need stable sub-effect
  idempotency or finer-grained effect records.
- Broad related regressions passing does not reduce the severity of the
  independently reproduced frozen-slice defects.

## Required disposition

Return the slice to a sole implementation writer. Re-run this review after:

- staged platform semantic validation is wired;
- recovery is hash-verified and removes created directories;
- post-commit effects are durably rehydratable/idempotent;
- strict aliases are removed;
- dry-run executes pure common preflight;
- dedicated tests include the negative probes above.
