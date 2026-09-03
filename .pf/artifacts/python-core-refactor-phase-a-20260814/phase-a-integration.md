# Python Core Refactor — Phase A Integration

## Result

Phase A is complete as an audit-and-design phase. No product Python source was changed.

The selected direction is **process-centric modular core with thin CLI, runtime, MCP, and hooks adapters**. The first behavior-preserving vertical slice is **Process Definition**: catalog resolution, authoring normalization, contract validation, doctor use cases, and process-definition route/handoff checks.

## Accepted evidence

- Process contract, adapter/runtime, public-surface, dependency, and compatibility inventories.
- Target architecture and phased refactor plan.
- Migration-impact report: extraction is behavior-preserving; cleanup of legacy aliases is a separate change decision.
- Independent architecture review and final reconciliation review.

The public-surface inventory was redacted and rechecked after its first version included private absolute paths and unsupported claims. Only the redacted artifact is accepted as evidence.

## Settled implementation order

1. **Phase B** — package/import foundation only; no partial movement of process semantics.
2. **Phase C** — shared Process Definition API used by CLI, runtime host, MCP facade, and hooks.
3. **Next slice** — event ingress, projections, work state, runtime transport, and worker lifecycle.

Compatibility fallbacks remain outside canonical Core. The first shared slice must not absorb event/work-state semantics.

## Verification

- All 17 Phase A tasks are in `done` state and pass `task-doctor`.
- `run-doctor` passes while the run is active.
- The recovery reviewer compared the recovered target architecture with the preserved original: only the intended Phase 3 block differs, and no appended sync report remains.
- `git diff --check` passes.

## Follow-up

Create a separate implementation run for Phase B. Its first worker tasks must establish the package/import seam and characterization gates before extracting process-definition behavior.
