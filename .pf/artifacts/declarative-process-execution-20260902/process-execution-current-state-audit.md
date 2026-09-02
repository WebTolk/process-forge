# Process Execution Current State Audit

Status: ready_for_review
Date: 2026-09-02
Scope: current `dev` implementation, not historical design documents

## Current execution path

`pf.work.start` is implemented by `GovernedWorkBootstrapService` in
`src/processforge_core/garage.py`. It checks snapshot freshness, resolves the
selected Process, chooses either `preferred_stage` or the first declared stage,
and writes a Run and Assignment directly. It does not use a lifecycle service.

`pf.work_state` currently returns the broad Garage context summary. The richer
runtime-host state is assembled separately in `tools/pf_runtime/host.py` from
assignments, worker state, and the stage-obligations projection. Neither path
owns a stage transition operation.

Run and Assignment CRUD and completion live in `tools/processforge.py`.
Completion is manual: `task-complete` updates Assignment and Run task status;
`run-complete` then marks the Run completed and renders summary/handoff files.

## Existing reusable capabilities

- ProcessCatalog resolves active core, official, custom, user, and legacy YAML.
- Process YAML already declares ordered stages, required inputs, produced
  artifacts, entry/exit gates, automation bindings, stage completion, and run
  completion.
- Assignment already has a durable `stage` field.
- The ProcessForge event envelope and append-only NDJSON journal already exist.
- Stage obligation projectors already derive deterministic readiness from
  Process declarations, Assignments, required outputs, and verification events.
- Existing low-level Run/Task commands provide compatibility and diagnostics.

## Gaps against the master prompt

1. No universal `ProcessExecutionService` owns start/state/transition/complete.
2. No high-level `pf.work.transition` API exists.
3. High-level work state does not expose the current stage contract, blockers,
   required evidence, or allowed outcomes.
4. Process version, fingerprint, effective definition, and context snapshot are
   not pinned when Garage work starts.
5. Stage transitions and branching are not represented independently from
   cross-process `process_transitions`.
6. Stage lifecycle events and deterministic stage history are absent.
7. A final stage cannot complete Assignment and Run without low-level commands.
8. Garage start still exposes `preferred_stage` as an ordinary public input.

## Infrastructure observation

The current project snapshot becomes stale immediately after refresh, and
Garage `pf.work.start` is blocked with `snapshot_not_fresh`. The implementation
run was therefore created through the compatible low-level file-first commands.
This is recorded as an existing project-state blocker, not repaired here.

## Implementation boundary

The change will add a declaration interpreter and thin adapters. It will not
add process plugins, Python process classes, callbacks, dynamic imports, an
expression language, or executable code in Process YAML.
