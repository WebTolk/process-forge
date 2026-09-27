# Work and Execution Contract

This is the accepted design contract for the vision-alignment work. It separates
existing behavior from the additive implementation steps below. A design name in
this document is not an advertised command until its implementation is delivered.

The base workflow is file-first and can run without a model, MCP, a Ledger session,
or a Runtime daemon. A provider or transport adapter cannot widen its permissions.
See [declarative process execution](declarative-process-execution.md),
[context capsules](context-capsule.md), and [session telemetry](session-telemetry.md).

## Implementation status

| Area | Existing behavior | Target implementation |
|---|---|---|
| Work identity | T02 pins material; T03 adds [normalized immutable assignment intent](work-context.md) and explicit scope/source/capability contracts in source | Integrated installed/actual-host qualification remains T06 |
| Capsule | T03 shares one complete execution contract across both builders; old v1 envelopes remain readable | Restricted legacy execution requires a successor; no in-place overwrite |
| Search/resolve | T02 implements [Work-scoped reads](work-resources.md) with pinned material and current authorization; project navigation remains available | Installed and real-host integration qualification remains T06 |
| Provider ingress | T04 implements [trusted provider adapters](provider-adapters.md), raw-first admission and common Host authorization in source | Installed and actual-host integration qualification remains T06 |
| Worker preparation | T05 implements [bounded prepared input](prepared-input.md), explicit current grants, neutral shell lifecycle and per-attempt collection receipts in source | Integrated and actual-host acceptance remains T06 |
| Diagnostics | T09 implements the [optional diagnostic contract](diagnostics.md), bounded sinks/configuration/export in source; mandatory journals are unchanged | Installed and real-host integration qualification remains part of T06 |

## Identity and immutable intent

Work identity is `(project_id, run_id, assignment_id)`. An immutable context has its
own id, contract version and checksum. It pins the process definition/version/hash,
snapshot generation/checksum, selected resources and material identities, scope,
required inputs/outputs, capabilities and rebuild policy. An execution attempt is
separate: retries change attempt identity, not the meaning of the assigned Work.

The assignment-intent digest covers objective, explicit scope/actions, inputs,
outputs, capabilities, access grants and coordination restrictions. It excludes
legitimate lifecycle state such as stage/status/history, timestamps and evidence.
Provider/model selection and diagnostic verbosity are execution preferences, not
permission-bearing Work identity. Security restrictions still constrain preferences.

The stage view is derived from the pinned process plus current assignment state.
It contains stage id, allowed outcomes, required artifacts/gates, current evidence,
and effective resource subset. A stage transition must never rewrite the immutable
context or replace it with the newest project snapshot.

The existing capsule envelope remains readable as v1. New complete capsules add a
versioned `execution_contract` block, starting at `contract_version: 1`. An absent
block means legacy, not unlimited access. Unknown versions cannot be executed by
guessing the nearest known format.

Illustrative target contract fragment, not a currently accepted launch request:

```yaml
execution_contract:
  contract_version: 1
  identity:
    project_id: example
    run_id: example-run
    assignment_id: inspect-input
    context_id: inspect-input-context-1
  assignment_intent_checksum: "sha256:<intent-digest>"
  snapshot:
    id: example-generation
    checksum: "sha256:<snapshot-digest>"
  process:
    id: inspection
    version: 1.0.0
    fingerprint: "sha256:<process-digest>"
  resources:
    - id: example.guide:root
      generation: v1
      material_kind: fulltext
      fingerprint: "sha256:<declared-material-digest>"
  scope:
    allowed_read_files: [docs/input.md]
    allowed_files: [.pf/artifacts/result.md]
    forbidden_files: [secrets/**]
    allowed_actions: [read, write_artifact]
    forbidden_actions: [write_product]
  required_sources:
    - path: docs/input.md
      checksum: "sha256:<input-digest>"
  outputs:
    - id: result
      path: .pf/artifacts/result.md
      required: true
  capabilities:
    required: [repository_read, markdown_editing]
    optional: []
  worker_may_rebuild_context: false
```

The example omits envelope/transport details intentionally. Empty allowlists grant
nothing. A required output is an obligation, not permission to write outside scope.
Analysis-only assignments cannot gain product write permission from a default.
PF's own state/evidence writes are service operations, not an unrestricted worker grant.

## Resource reads and current authorization

Effective access is the intersection of pinned Work grants, current project
authorization, the stage subset, and available authorized material/capabilities.
Explicit denies take precedence. A current grant for resource B does not add B to
an older Work that selected A. Revocation of A prevents further reads even when
an old snapshot or cache still contains A.

An omitted stage subset inherits the Work grants. An explicit empty subset grants
no resources. A subset referring to an unknown or unpinned resource is invalid;
it cannot silently expand or silently disappear from the diagnostic result.

Resource identity includes the selected id, generation/version and a verifiable
fingerprint of the declared material. Metadata-only sources bind metadata, not
every file beneath a directory. Content sources require a bounded verifiable
manifest/digest for the material they expose. A missing, changed or unverifiable
required input blocks preparation/read with a specific reason. Large input trees
are not copied automatically; declared budgets and supported version evidence
determine whether preparation is possible.

Mutable Work output artifacts are journal/evidence objects. They must not be
silently treated as a frozen reference corpus that invalidates itself whenever
the next stage writes its report. Required immutable input files still carry
their own checksums, including when they originated from an earlier Work.

Project navigation remains explicitly project-scoped. The additive source
`work-search`/`work-resolve` and `pf.work.search`/`pf.work.resolve` routes use the
same application service and require explicit Run/Assignment/context selectors. Responses
carry Work/context/resource generation provenance. A supplied context must belong
to that Work; a bound session must also authorize the project. No transport may
infer broader permissions from an omitted selector.

Index readiness, authorized coverage and resolvable navigation are distinct facts.
A fresh Workplace index can contain no documents for a project's selected grants.
A declared resource can have an unresolved local target. Neither case is proof
that the selected content is available to a Work.

## Context replacement and legacy records

Never overwrite a pinned capsule. A context change requires an explicit governed
successor Work, or an explicitly supported migration that writes a new versioned
context and preserves predecessor ids/checksums/reason and historical evidence.
There is no silent migration, no fallback to today's resource with the same name,
and no privilege inheritance merely because an old record omitted scope.

Existing v1 records remain readable and existing project navigation retains its
meaning. A restricted new execution/read path may adapt a legacy record only
when it can deterministically prove the required identity and grants. Otherwise
it returns `legacy_contract_incomplete` and identifies missing fields plus the
supported successor/migration action. Lifecycle mutations alone do not count as
assignment-intent changes. Actual changes to scope/objective/inputs do.

## Trusted adapters and prepared execution

Trusted registration selects an adapter implementation before ingress. An event
can name an adapter, but cannot provide an import path, executable or trust policy.
Unknown adapters are denied/quarantined. Provider-specific payload interpretation
and provenance checks belong in the registered adapter. Common Host retains
raw-first durability, registry identity, project/session/attempt binding, path and
hash authorization, deduplication, quarantine and replay invariants.

Preparation resolves only granted resources, validates required material and
capabilities, and writes a bounded private input manifest for one Work/context/
attempt. Public contracts use portable ids/path references; absolute resolved
paths remain private. A driver delivers the prepared input by file/CLI/MCP as
appropriate. It does not bootstrap another Work or reselect process/scope.

Missing access blocks preparation before launch. Retry produces a distinct
attempt while retaining Work identity; result collection checks attempt and
evidence hashes and remains idempotent after restart. A generic shell executor
can run offline without MCP. Actual OS sandbox enforcement is a driver/runtime
capability; a prompt or declarative grant alone is not an OS security boundary.

## Diagnostic contract

The optional Python logger exposes `log(level, message, context)` and equivalent
level methods, placeholder interpolation, safe arbitrary context handling and
an exception context slot. This follows the interface ideas of
[PSR-3](https://www.php-fig.org/psr/psr-3/), without claiming PHP compliance.

| Canonical severity | Python numeric mapping |
|---|---:|
| debug | 10 |
| info | 20 |
| notice | 25 |
| warning | 30 |
| error | 40 |
| critical | 50 |
| alert | 60 |
| emergency | 70 |

The common Python levels retain their standard values; notice/alert/emergency
use explicit PF values through the bridge. Export preserves canonical severity.
Unknown severity is rejected, even when output is disabled. PF does not reconfigure
the application's root logger. See the official
[Python logging reference](https://docs.python.org/3/library/logging.html).

Profiles describe detail: quiet defaults to warning; normal to info; diagnostic
and trace to debug. Trace adds bounded spans/stack metadata, not a ninth severity.
Off/no-op disables only optional diagnostics. Process journal, required evidence,
audit obligations and explicit error responses retain their own failure semantics.

Configuration precedence is defaults, project, Work/session, invocation. A more
local override cannot relax locked security/storage ceilings. Effective values
and sources are inspectable; temporary diagnostic/trace overrides have explicit
expiry/volume limits and fall back when expired. Scope/correlation do not leak
between parallel requests. Session is null/absent when there is no real session.

Records include UTC time, severity, component, stable event/error code, sanitized
message/context, available request/Work/attempt/snapshot/build identity and duration.
Redaction runs before every sink and before interpolated output. Raw prompts,
payloads, environment dumps and file contents are not collected by default, even
in trace. Unsafe string conversion or serialization of arbitrary context must not
break the operation. Disabled detail does not construct expensive context.

JSONL/private and human-readable stderr sinks share the record contract. Protocol
stdout stays protocol-only on success and failure. Bound record/string/depth/stack/
span size, rotation, retention and aggregate quota before deployment. Sample only
optional detail, expose truncation/drop counters, and make lost serious diagnostics
visible through a non-recursive bounded fallback/health signal. A sink failure
must not hide the original result or exception; mandatory journal failure is not
downgraded to best-effort logging.

Diagnostic export is read-only and filtered by request/Work/time interval. It
contains safe effective config, build/provenance, snapshot ids/hashes and freshness
reasons, bounded related diagnostics and a manifest including redaction/truncation.
Public export sanitizes private paths and secrets; it neither repairs context nor
restarts services. This protects diagnostic output and does not implement the
separate outbound-model privacy design.

## Decision and acceptance matrix

Diagnostic names below define target semantics. They are not a claim that every
name is already emitted by the current implementation.

| ID | Positive example | Negative scenario and diagnostic | Compatibility rule |
|---|---|---|---|
| D01 | Two attempts share one Work/context | Caller supplies another Work's context: `work_context_mismatch` | Derive legacy identity only from unambiguous stored Run/Assignment, never session name |
| D02 | Stage advances while intent digest stays stable | Objective/scope changes against old capsule: `assignment_contract_changed` | Preserve raw legacy checksum evidence; do not reinterpret lifecycle status as changed intent |
| D03 | Pinned A remains authorized and unchanged | A revoked/changed/missing: `resource_revoked` / `resource_changed` / `resource_unavailable` | Old selection is never a bypass of current authorization; unverifiable legacy material requires migration |
| D04 | Stage selects A from Work {A,B} | Stage requests C: `stage_resource_outside_work`; [] returns no grants | Omitted subset inherits pinned grants; explicit [] is not omission |
| D05 | Analysis reads input and writes its allowed report | Empty write scope or product write: `scope_denied` | Missing legacy scope never means repository-wide access |
| D06 | Granted input/output paths and required capability verified before launch | Missing source/capability or output outside scope: `required_source_missing` / `capability_missing` / `output_scope_denied` | Optional capabilities stay optional; missing required facts cannot be guessed |
| D07 | Successor context records predecessor and reason | In-place old capsule rewrite: `immutable_context_changed`; unsupported version: `contract_version_unsupported` | Legacy remains readable; incomplete restricted execution gets `legacy_contract_incomplete` |
| D08 | Registered non-Codex fixture normalizes a valid event | Unknown adapter or identity/path/hash spoof: `adapter_untrusted` / `provenance_rejected` | Existing Codex adapter keeps its security checks; common raw/dedup/replay behavior is preserved |
| D09 | Offline generic-shell consumes one prepared manifest | Attempt/result mismatch or unprepared launch: `attempt_mismatch` / `input_not_prepared` | Manual driver remains available; driver choice cannot alter Work scope/process |
| D10 | log(warning) equals warning(); trace remains debug profile | Unknown level: `invalid_log_level` | Existing journal/telemetry facts remain independent of optional logger |
| D11 | Invocation temporarily enables component diagnostic within ceilings | Override weakens lock: `diagnostic_policy_locked`; expiry restores baseline | Defaults work without config; absence of a session does not create one |
| D12 | Bounded redacted record reaches JSONL/stderr | Disk-full/serializer fault: `diagnostic_sink_failed` plus loss counters | Operation result remains intact; mandatory evidence errors remain fatal under their contract |
| D13 | Request-scoped sanitized export has manifest | Wrong Work/time selection or oversized export: `diagnostic_export_invalid` / `diagnostic_export_truncated` | No raw transcript/environment by default; no service repair during export |
| D14 | Work A reads A while project navigation sees current B | Work asks B or has zero indexed grant coverage: `resource_not_in_work` / explicit coverage status | Existing project APIs retain their scope; CLI/MCP invoke identical Work rules |
| D15 | Public path_ref resolves into private prepared input | Absolute path in public grant or traversal: `private_path_forbidden` / `path_scope_escape` | Private runtime remains private; no claim of sandboxing from declarative scope alone |

T06 composes these cases across transports, two simultaneous Work contexts,
restart/retry, provider substitution and all diagnostic profiles. T08 live MCP
acceptance must be repeated after implementation changes; a subprocess smoke or
successful initialize alone is insufficient.
