# Work context and execution contract

ProcessForge source now uses one shared context builder for governed Work capsules and the `assignment-capsule` command. The existing capsule envelope stays version 1; new capsules add a versioned `execution_contract` block. This block makes the assignment’s intent and permissions explicit in a form both creation paths can validate. It does not replace the run/assignment journals or make the worker’s filesystem an OS sandbox.

See [Work and Execution Contract](work-execution-contract.md) for the wider vision-alignment contract, [context capsules](context-capsule.md) for the envelope and launch role, and [Work-scoped resource reads](work-resources.md) for T02’s pinned resource material and current-access rules.

## What the block records

Explicit operator egress intent creates `contract_version: 2`, binding the
policy, detector implementation, recipient, purpose, minimum enforcement and
budgets. v1 stays unchanged and cannot claim strict egress. See the
[managed egress engine](egress-engine.md) for creation, successors and qualification.

`execution_contract.contract_version: 1` includes:

- identity (`project_id`, `run_id`, `assignment_id`, `context_id`) and the normalized assignment-intent checksum;
- pinned project snapshot and process identity, plus selected resource ids and a digest of their T02 bindings;
- explicit file scope, allowed and forbidden actions, immutable required-source checksums, and output/report obligations;
- required and optional capability records, workspace grants, resolved stable parameters, coordination restrictions, source budgets, and readiness blockers.

The assignment-intent digest covers the objective, execution security mode, permissions, sources, context-artifact declarations, outputs, capabilities, workspace access, process/specialization choices, and coordination restrictions. A change to these facts needs a successor context. Stage, status, stage history/evidence, timestamps, result, retries/session identity, and provider/model/reasoning or diagnostic preferences are lifecycle or execution preferences; they do not redefine that intent. A changed required immutable source is separately detected by its recorded checksum.

Stage obligations are derived from the pinned process and the assignment’s current stage. Moving to another stage must not rewrite the capsule or silently select a newer snapshot. The outer capsule remains the byte-pinned record for governed Work; the contract’s own checksum detects internal changes and malformed content.

## Scope, actions, and outputs

Paths in the public contract are project-relative. Private absolute paths are rejected. A read or write requires both an allowed action and a matching allowlisted path; forbidden actions and paths win. An empty allowlist grants nothing. Ownership metadata cannot widen an empty `allowed_files` list. `write_artifact` is limited to `.pf/artifacts/` and still requires a matching allowed path. Required outputs describe obligations: they do not grant permission to write their paths.

When actions are omitted, the builder derives a conservative set from the declared execution mode and path scope. Analysis/read-only/planning modes cannot gain `write_product` through defaults or contradictory flags. ProcessForge’s own journal and evidence writes are service operations, not additional worker file permissions. The contract describes permission policy; it does not enforce a kernel-level sandbox around arbitrary tools.

## Inputs and readiness

`required_sources` and assignment `input_artifacts` declare project-relative input
files. Repeated declarations cannot discard an earlier checksum; conflicting
checksums produce `required_source_conflict`. Review, completion and handoff
obligations are also part of immutable intent. Malformed execution modes and
permission booleans fail validation instead of enabling capabilities by coercion.

Required immutable inputs are regular project files captured with byte checksums. The current limits are 128 files, 1 MiB per file, and 8 MiB total. Paths must stay within the project and cannot traverse symlinks; missing, changed, unreadable, special, oversized, or over-budget sources produce explicit blockers. Assignment and snapshot references remain in the envelope for navigation and lifecycle, not as self-hashed immutable source bytes. Mutable context artifacts are declarations, not frozen corpus snapshots.

Required capabilities are resolved against declared providers. Missing required capabilities block worker preparation; missing optional capabilities are retained as optional. The contract records readiness and specific blockers at creation, and worker preparation revalidates the contract, required sources, and required capabilities before it launches. Capability readiness is a declaration/provider check; it does not guarantee that an external executable or service will remain available.

## Standalone assignments and legacy capsules

A Work identity also requires a matching persisted Run and exact assignment
membership. A claimed run id alone is insufficient. During governed creation the
same check uses the service's new in-memory Run before it is persisted. Reuse and
worker preparation check persisted membership and any recorded capsule byte pin.

A legacy task-batch Run with no process pin can explicitly create a new complete
assignment capsule. That one-time capture is marked `legacy_run_new_context` in
its process pin; future reuse uses the captured definition. A present but corrupt
Run pin is blocked. This does not rewrite an older capsule or migrate the Run.

A standalone assignment without a run has `identity.kind: assignment`. It can produce a readable assignment context, but it is not represented as a governed Work; readiness records the missing Work/process identity. Worker preparation requires a ready complete contract and will request a successor Work when the assignment cannot satisfy that condition.

Older capsules without `execution_contract` remain readable as legacy records. Missing permissions are never inferred as broad access: restricted preparation reports `legacy_contract_incomplete` and asks for a successor context. Unknown contract versions fail explicitly. Capsule creation never overwrites an existing immutable capsule; `--force` can affect the separate overlap check, but does not replace a context. Preserve the old capsule and create a new governed successor when intent changes.

## Source boundary

These behaviors describe the current source checkout. They do not claim that an installed Core or a real host has been qualified. Installed and host integration acceptance belongs to T06; source-level smokes and schema checks are not a substitute for that boundary.
