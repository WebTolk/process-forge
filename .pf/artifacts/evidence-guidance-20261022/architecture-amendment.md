# Architecture refinement

2026-10-22. Keep the large process_execution facade unchanged. Current-stage
guidance is projected by WorkStatePolicy; request errors by TransitionRejectionPolicy.
Prospective next-entry gates come from the pinned process and each offered outcome,
explicitly conditional and unevaluated. They are never reported as missing merely
because an outcome exists. This covers transition-only entry checks without a new
decision path or modifying the facade. All matcher semantics, codes and lifecycle
decisions remain authoritative. Approved stage plans remain unchanged.
