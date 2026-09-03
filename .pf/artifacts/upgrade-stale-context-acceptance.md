# Upgrade/Stale Context Acceptance

Status: partial pass

Observed in this run:

- stale snapshot blocked baseline capsule creation;
- stale snapshot blocked acceptance capsule creation;
- explicit `project-context-refresh` returned `STATUS: fresh` both times;
- search maintenance tick ran during refresh.

Residual:

- automated safe stale reconcile and semantic-change operator diff were not
  implemented here.
