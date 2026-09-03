# Process Transitions

Process transitions are explicit routes between authored processes. They are stored in `.pf/process-routes.yaml` for a project or in a workplace registry when the route is shared.

A route defines source process, target process, handoff mode, required receiving role, input artifacts, expected output artifacts, and return behavior. Supported modes are `wait_for_result`, `delegate_and_continue`, `consultation`, `final_transfer`, `fork`, and `return_required`.

ProcessForge treats a transition as a contract, not as a status rename. The handoff package records what crosses the boundary and how the original process can continue.

A process transition is a Work boundary, not a stage transition. The receiving
process starts a new Run and capsule; it does not mutate the sender's active
process or specialization set. Garage may advise whether to preserve or refresh
the user session, but it does not orchestrate either action.

The advisory is durable enough for a later `pf.context` to locate the newest
relevant completed handoff. It is compact (run, process, handoff, next-process
recommendation) and does not replay the previous process graph or event history.

Agent Director owns transition routing decisions, handoff readiness, lease
coordination, and continuation decisions. The Process Execution Inspector may
verify assigned task runtime state for a route, but it must not choose the
route, grant the lease, or finalize the handoff. The Worker performs the
assigned capsule task.
