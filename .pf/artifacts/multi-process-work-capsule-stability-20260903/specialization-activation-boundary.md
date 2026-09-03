# Specialization activation boundary

Status: ready_for_review

Specializations remain resource profiles, not processes or stage owners. A project may authorize several specialization ids, but a Work activates only the set selected for its one active process.

At `pf.work.start`, the selected set is copied into Run, Assignment and capsule alongside the process pin. `pf.work.state` reads this pin rather than the mutable project authorization list. A specialization change therefore requires a new Work boundary, normally after a handoff/process transition.

This preserves the existing data-driven capability model: no core catalogue of role, platform, tool, or specialization identifiers is introduced.
