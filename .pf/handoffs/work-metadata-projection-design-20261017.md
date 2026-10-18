# Handoff: primary architect -> operator / future implementation

Objective: shared Work metadata projection design for pf.context; no product code.
Current status: architecture.md, implementation-plan.md, decision-log.md and source-informed review are complete; native terminal closeout and doctors are recorded in closeout.json. This Work must not be resumed after completion.
Input artifacts: prior pf-context-latency-20261017 diagnosis, current YAML read contract, OOP clarification/domain map/refactoring plan, current summary/catalog/selection/completion/publisher owners.
Files changed: only this engagement's artifacts/handoff; private device configuration changed separately by explicit user request through installed native CLI.
Files not to touch: old capsules/approved inputs, unrelated dirty files, product source and release candidate.
Known issues: future implementation is absent by user instruction; cold parsing and linear content checks remain; working-set fit and actual speed are unmeasured; filesystem read pass is not a global transaction.
Required checks: future implementation parity, pending completion/read-after-write/same-stat matrix, cold/warm measurements and separate source/archive/install/Runtime/connected-MCP qualification where authorized.
Next recommended action: discuss the concrete design. Implement only after a new explicit instruction, with a new bounded Work and the architectural inputs pinned. No automatic update/restart.

Device setting: native CRUD and readback confirm logging.raw_hooks=false, logging.events=true; current project inherits. This disables optional raw history, retains normalized events and chat, and does not delete earlier data. Pending delivery/admission state remains. See device-logging-policy.md. Proposed terms: «сырые хуки», «события PF», «переписка».
