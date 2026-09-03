# Garage Context Contamination Audit

Status: passed

`pf.context` exposes a compact process catalogue (`default`, `allowed` IDs) before Work begins. It does not expose stage definitions. `pf.work.state` exposes exactly the selected process and the active specialization/resource IDs of the current Work.

Evidence: `tools/smoke_multi_process_work_capsule.py` passed `smoke_project_multiple_allowed_processes`, `smoke_work_start_ambiguous_process_choice_required`, `smoke_active_work_has_single_process`, and `smoke_work_capsule_does_not_union_allowed_processes` on 2026-09-03.

Residual risk: candidate labels are resolved only to render the compact choice response; no candidate definition is written into the Work capsule.
