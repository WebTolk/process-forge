# Handoff Contracts

A handoff package lives under `.pf/handoffs/<handoff-id>/`.

The package contains `handoff.yaml`, `handoff.md`, `input-manifest.yaml`, `expected-output.yaml`, and `return-package.yaml`. `handoff-status` reports whether the package is still `waiting_for_agent`, ready for an available role, accepted, returned, finalized, or escalated.

`handoff-return` requires concrete returned artifacts. A handoff is not complete just because a worker says it is complete; ProcessForge checks the expected files and records the return package.

Handoff state is coordinated by Agent Director, not by the Process Execution
Inspector. The inspector can report whether an assigned worker task produced
runtime proof and required outputs; it does not accept, return, finalize, or
route handoffs. See
[Director, Ledger, Inspector, And Worker Boundary](director-ledger-inspector-boundary.md).
