# Process Transitions

Process transitions are explicit routes between authored processes. They are stored in `.pf/process-routes.yaml` for a project or in a workplace registry when the route is shared.

A route defines source process, target process, handoff mode, required receiving role, input artifacts, expected output artifacts, and return behavior. Supported modes are `wait_for_result`, `delegate_and_continue`, `consultation`, `final_transfer`, `fork`, and `return_required`.

ProcessForge treats a transition as a contract, not as a status rename. The handoff package records what crosses the boundary and how the original process can continue.

Agent Director owns transition routing decisions, handoff readiness, lease
coordination, and continuation decisions. The Process Execution Inspector may
verify assigned task runtime state for a route, but it must not choose the
route, grant the lease, or finalize the handoff. The Worker performs the
assigned capsule task.
