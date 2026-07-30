# ADR: failure-atomic authoring transactions and canonical platform migration

- ADR id: `pre-release-remediation-transaction-design-20260730`
- Date: 2026-07-30
- Status: accepted for implementation
- Run: `pre-release-remediation-20260730`
- Assignment: `remediation-transaction-design-20260730`
- Related findings: `PF-AUD-010`, `PF-AUD-011`, `PF-AUD-019`, process-create/dry-run part of `PF-AUD-020`
- Depends on: `pre-release-remediation-schema-authority-20260730`
- Strict-contract policy: `pre-release-remediation-no-compatibility-20260730`

## Context

The affected commands mix planning, authoritative writes, registry publication
and audit effects in one procedural sequence. A failure after an early write can
leave a resource visible although its doctor failed, or can leave two files
describing different versions of the same entity.

The transaction boundary must include every authoritative write derived from one
user action. Proposal files, ordinary events, reports and hook deliveries are
not authoritative resource state. They must not be written before preflight and
must not be used as a substitute for a transaction journal.

Serena was used first, but its Python symbol backend was unavailable for this
checkout (`Active languages: []`). The exact graphs below were therefore traced
with narrowly scoped symbol and line reads in `tools/processforge.py`.

## Observed write graphs

### `command_platform_create`

Current symbol graph:

```text
command_platform_create
  -> normalize_platform_id
  -> resolve_platform_root(mode="write" when --apply)
       -> upsert_registry_entry(registries/platform-contract-roots.yaml)
          [conditional: missing/empty registry]
       -> root_path.mkdir(...)
  -> write_resource_proposal
       -> runtime/resource-management/proposals/<slug>.yaml
  -> append_workplace_resource_event(platform.authoring.started)
       -> runtime/events/events.ndjson
  -> write_authoring_text x12
  -> upsert_registry_entry(registries/platforms.yaml, status=available)
  -> append_workplace_resource_event(platform.contract.created)
  -> append_workplace_resource_event(platform.contract.linked)
  -> command_platform_contract_doctor
  -> append_workplace_resource_event(platform.contract.doctor.passed|failed)
  -> append_workplace_resource_event(platform.authoring.completed) [unconditional]
```

The twelve entity files under
`<platform-root>/platform.<id>/` are:

```text
platform-contract.yaml
README.md
project-types.yaml
capabilities.yaml
knowledge.yaml
templates.yaml
tools.yaml
mcp.yaml
processes.yaml
artifacts/platform-contract-authoring-report.md
reviews/platform-contract-authoring-review.md
handoffs/platform-contract-ready-handoff.md
```

Failure points and current consequences:

- `resolve_platform_root(mode="write")` is a mutating resolver. It can create a
  root registry and directory before any collision, registry or dependency
  preflight.
- Proposal and `platform.authoring.started` are written before the target
  collision check.
- Each target file is written independently. A parent-type or I/O failure leaves
  a partial directory.
- `registries/platforms.yaml` publishes `status: available` before the doctor.
- A failed doctor returns nonzero only after the active registry entry exists.
- `platform.authoring.completed` is emitted for both doctor outcomes.

### `command_knowledge_add_url` and `command_knowledge_add_resource`

Current common graph:

```text
command_knowledge_add_*
  -> resolve_package_root
  -> emit_package_root_resolution_event
       -> runtime/events/events.ndjson
  -> normalize/build resource
  -> write_resource_proposal
       -> runtime/resource-management/proposals/<slug>.yaml
  -> append_workplace_resource_event(requested)
  -> load_workplace_package_manifest
  -> upsert_resource [memory only]
  -> write_package_manifest_and_index
       -> package.yaml write
       -> indexes/resource-index.yaml write
  -> append success events
  -> write_resource_management_report
```

`command_knowledge_add_resource` has an additional hidden write:

```text
normalize_resource_record(register_private_path=True)
  -> ensure_private_resource_path
  -> upsert_registry_entry(registries/private-resource-paths.yaml)
```

This registry update happens before the proposal and before package/index
publication. `private-resource-paths.yaml` currently has neither a shipped JSON
Schema nor a mapping in `upsert_registry_entry`.

`write_package_manifest_and_index` writes `package.yaml` before creating/writing
`indexes/resource-index.yaml`. If `indexes` is a regular file, or if the second
write fails, the manifest remains changed. Resolution, proposal and requested
events are also already durable.

### `command_platform_contract_install`

Current graph:

```text
command_platform_contract_install
  -> write_resource_proposal
  -> workplace/platforms/<id>/platform.yaml       [legacy layout]
  -> upsert_registry_entry(registries/platforms.yaml)
  -> append_workplace_resource_event(platform.contract.updated)
  -> write_resource_management_report
```

The command neither uses the canonical platform root nor invokes the platform
doctor. For an existing logical id it can redirect the registry from
`platform-contracts/platform.<id>/platform-contract.yaml` to the legacy path and
leave the canonical directory orphaned.

### `command_process_create`

Current one-shot graph:

```text
command_process_create
  -> normalize answers
  -> process_authoring_paths
  -> write_yaml_file(answers.yaml)
  -> write_yaml_file(draft.process.yaml)
  -> questions.md write
  -> append_authoring_log
  -> emit_process_event x3
       -> .pf/runtime/events/events.ndjson
       -> dispatch_hooks
            -> conditional hook outbox payload
            -> conditional hook result JSON
  -> command_process_authoring_apply
       -> require_flow_root                    [too late]
       -> logic-review.md write
       -> process YAML write
       -> prompt write
       -> process doc write
       -> seven example files
       -> apply-report.md write
       -> append_authoring_log
       -> emit_process_event x3 + hook fan-out
```

The private session has six final files:

```text
.pf/authoring/processes/<id>/answers.yaml
.pf/authoring/processes/<id>/draft.process.yaml
.pf/authoring/processes/<id>/questions.md
.pf/authoring/processes/<id>/logic-review.md
.pf/authoring/processes/<id>/authoring-log.md
.pf/authoring/processes/<id>/apply-report.md
```

The public/materialized files are:

```text
processes/<user|custom|core>/<id>.yaml
prompts/<id>-agent.md
docs/processes/<id>.md
examples/process-authoring/<id>/README.md
examples/process-authoring/<id>/answers.yaml
examples/process-authoring/<id>/draft.process.yaml
examples/process-authoring/<id>/logic-review.md
examples/process-authoring/<id>/process-authoring-<id>-report.md
examples/process-authoring/<id>/process-authoring-<id>-review.md
examples/process-authoring/<id>/process-authoring-<id>-handoff.md
```

On an uninitialized project, the first four session files and three events are
attempted before `require_flow_root` fails in
`command_process_authoring_apply`. Current dry-run delegates to
`command_process_authoring_start`, so it lists only four private session files
and omits all materialized outputs, the review/report files, events and
conditional hook effects.

## Decision 1: one transaction model

Introduce a small internal transaction model in `tools/processforge.py`:

```text
AuthoringWrite
  destination
  content bytes or staged directory
  role: entity | registry | audit
  policy: create | replace
  expected pre-image: missing | sha256

AuthoringPlan
  transaction_id
  command
  authoritative_writes
  registry_writes
  post_commit_effects
  validation callbacks
```

The common execution symbols are:

```text
preflight_authoring_plan
stage_authoring_plan
validate_staged_authoring_plan
commit_authoring_plan
rollback_authoring_plan
recover_authoring_transaction
render_authoring_plan
planned_registry_upsert
run_post_commit_effects
```

The transaction journal lives outside the authoritative resource and registry
trees:

```text
<runtime-root>/authoring-transactions/<transaction-id>/journal.yaml
```

It records destination, role, pre-image existence/hash, staged hash, backup
path, completed phase and rollback result. It must never contain secret values.

## Decision 2: ordered algorithm

### Phase A — pure preflight

Pure preflight performs no directory creation, proposal write, event append or
hook dispatch.

1. Require exactly one explicit mode: `--dry-run` or `--apply`. A command with
   neither or both fails without product-state writes.
2. Validate ids, input YAML, secret/path references and initialized project or
   workplace roots.
3. Resolve roots in read-only mode. `resolve_platform_root(mode="write")` is
   forbidden in preflight. A missing default root entry may be constructed only
   in memory and included as a planned registry write.
4. Build all final bytes in memory and compute the complete destination set.
5. Check containment, duplicate destinations, parent types, target collisions,
   immutable process id/version rules and cross-root ambiguity.
6. Parse and schema-validate every existing registry without fallback to an
   empty object.
7. Produce proposed registry documents in memory with
   `planned_registry_upsert`.
8. Validate the proposed entity and registry documents against authoritative
   schemas and run semantic checks that do not require published state.

If preflight fails, no ordinary proposal/event/report is written. An optional
failure record may be written only to the separate transaction/failure journal;
it is excluded from authoritative state and has no hooks.

### Phase B — staging

1. Create the write-ahead journal with state `preparing`.
2. Create one staging/backup area per destination filesystem, beneath the
   nearest controlled root on that filesystem.
3. Stage every entity and registry document and record its SHA-256.
4. Build a virtual view mapping final destinations to staged paths.
5. Run the same schema and semantic validators used by doctors against the
   virtual view.
6. Mark the journal `prepared` only after every staged postcondition passes.

The implementation must not invoke a doctor that can only resolve through the
live registry. Extracted pure check helpers accept a direct staged path and
proposed registry data; the CLI doctor and staged validator call the same
helpers.

### Phase C — authoritative commit

1. Record the next operation in the journal before each destination change.
2. Publish non-registry entity files/directories first using same-filesystem
   rename or `os.replace`.
3. Preserve every replaced pre-image in the transaction backup area.
4. Verify the committed entity bytes and direct-path postconditions.
5. Publish all registry documents last, using atomic replacement. Platform
   `status: available` appears only in this final registry image.
6. Verify live resolution and hashes.
7. Mark the journal `committed`.

For multiple filesystems, physical all-or-nothing atomicity is impossible.
Failure atomicity is supplied by the write-ahead journal, per-filesystem staging,
pre-image backups and reverse-order rollback. An incomplete journal blocks the
next mutation until `recover_authoring_transaction` either completes a
fully-verifiable commit or restores every pre-image.

### Phase D — rollback

On any exception before `committed`:

1. stop publishing new destinations;
2. restore registry pre-images first if a registry replacement occurred;
3. restore entity pre-images and remove newly published entity paths in reverse
   order;
4. verify hashes against the journal;
5. mark `rolled_back`, or `recovery_required` if any restore cannot be proven;
6. write no success/completed event and dispatch no hook.

A `recovery_required` transaction is a hard doctor/mutation failure. It must not
be represented as a normal active or completed resource.

### Phase E — post-commit audit and hooks

Only after `committed`:

1. persist the proposal/audit record describing the already committed plan;
2. persist the success report;
3. append non-terminal events;
4. append `authoring.completed` last;
5. dispatch configured hook/outbox effects with the transaction id as an
   idempotency key.

Audit or hook failure does not roll back authoritative state because a hook may
already have been dispatched. Instead the journal moves to
`committed_audit_pending`; replay resumes missing effects idempotently. The
implementation must not claim rollback of an already dispatched hook.

## Decision 3: command-specific plans

### Platform create

`build_platform_authoring_plan` produces the twelve canonical entity files,
optional planned `platform-contract-roots.yaml`, and the final
`platforms.yaml` entry. `validate_platform_staged_view` validates the staged
contract directly and resolves required resources against the proposed view.

The live platform registry remains unchanged until all entity validation has
passed. `platform.authoring.completed` is impossible when validation or commit
fails.

### Knowledge resource add

`build_knowledge_resource_add_plan` produces, in memory:

- the updated package manifest;
- the matching resource index from that same manifest object;
- when required, the updated private-resource-path registry document.

`normalize_resource_record` becomes pure. It returns the normalized resource and
an optional private-path registry intent; it does not call
`ensure_private_resource_path`.

`write_package_manifest_and_index` is replaced by, or becomes a wrapper around,
the transaction plan. Manifest and index are staged and validated as one unit.
The private-path registry is a registry-last write.

Two schema dependencies are required for full compliance:

- `schemas/private-resource-paths-registry.schema.json`;
- `schemas/platform-contract-roots-registry.schema.json`.

Both must be included in registry schema routing and shipped-schema validation.

### Process create

`build_process_create_plan` performs `require_flow_root` before constructing any
write path, then renders the complete session and public output set in memory.
The one-shot command stages all sixteen final files as one transaction:

- six session files;
- three primary materialized files;
- seven example files.

The authoring log is rendered as its final two-line logical state rather than
being appended during the commit. `command_process_authoring_apply` uses the same
materialization planner for an existing session, so the public apply path cannot
bypass the transaction.

The six current process events are post-commit effects. For every selected hook,
dry-run also declares conditional outbox/result patterns:

```text
.pf/runtime/hooks/outbox/<event-id>.<hook-id>.json
.pf/runtime/hooks/results/<delivery-id>.json
```

Custom hook paths resolved from `hooks.yaml` are reported as conditional
destinations. They are not staged as authoritative process files.

## Decision 4: canonical platform layout only

All new platform writes use:

```text
<platform-root>/platform.<logical-id>/platform-contract.yaml
```

`command_platform_create` and `command_platform_contract_install` delegate to
the same `build_platform_authoring_plan` and transaction executor.
`platform-contract-install` may use a compact content profile, but it may not
choose another directory layout or bypass staged validation.

The unpublished legacy layout is unsupported invalid state:

```text
<workplace>/platforms/<logical-id>/platform.yaml
```

Any legacy file, registry target, or canonical/legacy coexistence is a blocking
preflight error with zero writes. Product code does not read, migrate, archive,
or repoint the legacy layout. Controlled dogfooding data is migrated outside
the public runtime before release.

## Decision 5: dry-run contract

Dry-run is pure. It does not write a proposal, journal, event, directory or
candidate file.

`render_authoring_plan` prints a stable, sorted plan with:

- destination;
- role (`entity`, `registry`, `audit`, `conditional_hook`);
- operation (`create`, `replace`, `append`);
- condition, when applicable;
- schema/postcondition used before commit.

The platform dry-run includes all twelve entity files, both possible registry
writes, proposal/report/event effects and transaction metadata placeholders.
The knowledge dry-run includes manifest, index, optional private-path registry,
proposal/report/events and any fallback-root creation. The process dry-run
includes all sixteen final files, event-log append and every conditional hook
fan-out pattern.

Apply records the same logical plan in its journal. The parity test compares
dry-run destinations with the applied journal, excluding physical
staging/backup paths and distinguishing conditional post-commit effects.

## Failure-injection test matrix

The transaction executor accepts a non-public injectable callback used by
tests. Production callers use a no-op callback; no public CLI failpoint is
introduced.

| Failpoint / condition | Platform | Knowledge | Process | Required result |
|---|---:|---:|---:|---|
| invalid mode: neither/both flags | yes | yes | yes | nonzero; no authoritative/audit writes |
| uninitialized root | n/a | workplace validation | yes | no `.pf` session/event creation |
| invalid/corrupt registry | roots/platforms | private paths | n/a | registry byte-identical; no entity |
| target parent is regular file | each target group | `indexes` is file | prompt/docs/example parent | no authoritative delta |
| duplicate/same-version entity | canonical id | resource/package collision policy | process id/version | fail in preflight |
| missing required dependency | required package/template/tool/MCP | invalid path ref | invalid process logic | no active/published state |
| after journal prepare | yes | yes | yes | journal rolled back; authoritative tree identical |
| after each staged item | yes | yes | yes | no authoritative delta |
| before first entity publish | yes | yes | yes | no authoritative delta |
| after each entity publish | all 12 | manifest, then index | all 16 | reverse rollback to exact hashes |
| before first registry publish | yes | private path | n/a | entity rollback; registry unchanged |
| after each registry publish | roots, then platforms | private path | n/a | all registries and entities restored |
| staged validator/doctor failure | yes | yes | yes | no `available`, no completed event |
| committed-state verification failure | yes | yes | yes | rollback before events/hooks |
| after commit, before audit | yes | yes | yes | state remains valid; journal `committed_audit_pending` |
| event append failure | yes | yes | yes | no authoritative rollback; replayable audit |
| hook outbox/result failure | n/a | n/a | yes | no rollback of prior deliveries; idempotent replay |
| any legacy layout or registry target | yes | n/a | n/a | fail in preflight; legacy/canonical/registry byte-identical |
| dry-run/apply plan parity | yes | yes | yes | exact logical destination parity |

Every negative test snapshots:

- authoritative entity roots;
- exact registry bytes;
- ordinary event stream bytes;
- hook outbox/result trees.

Only a declared transaction failure journal may differ after a rejected or
rolled-back operation.

## Sole-writer implementation scope

Implementation must start only after the current `tools/processforge.py` writer
lease is released. One agent owns the complete slice:

```text
tools/processforge.py
schemas/private-resource-paths-registry.schema.json
schemas/platform-contract-roots-registry.schema.json
tools/validate-process-forge-schemas.py
tools/smoke_remediation_transactional_authoring.py
tools/smoke_remediation_platform_layout_strict.py
tools/smoke_remediation_process_create_transaction.py
.pf/artifacts/pre-release-remediation-agents/transactional-authoring.md
```

Existing symbols to modify:

```text
resolve_platform_root
normalize_resource_record
ensure_private_resource_path
write_package_manifest_and_index
command_knowledge_add_url
command_knowledge_add_resource
command_platform_create
command_platform_contract_install
command_process_authoring_apply
command_process_create
build_parser
```

Existing leaf writers such as `upsert_registry_entry`, `write_yaml_file`,
`write_authoring_text`, `append_workplace_resource_event` and
`emit_process_event` remain reusable only behind the transaction phase that
permits them. They must not be called while building or validating a plan.

## Compatibility and consequences

- Existing valid canonical platform contracts remain in place.
- Legacy platform contracts are rejected as unsupported pre-release state.
- A command without an explicit mode fails and can never perform an implicit
  apply.
- Failed authoring may leave an audit-only failure journal, but not a visible
  resource, active registry entry, ordinary success event or hook delivery.
- Post-commit audit failure is distinguished from authoring failure; the
  resource remains committed and audit replay is required.
- The two missing registry schemas are implementation prerequisites, not
  optional hardening.

## Acceptance

This ADR is accepted for implementation when review confirms:

1. pure preflight has no hidden writers;
2. staged validators and public doctors share check logic;
3. registry publication is last;
4. hook side effects are post-commit and explicitly non-rollbackable;
5. dry-run contains the complete logical apply set;
6. every legacy platform layout is rejected before mutation;
7. every injected pre-commit failure restores exact authoritative bytes.
