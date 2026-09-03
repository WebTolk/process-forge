# Same-Session Continuation Acceptance

Status: passed

A terminal architecture Work returns only advisory next-work information and does not mutate the completed capsule. A subsequent `pf.work.start` produces a different run and assignment for implementation; session linkage remains advisory and optional.

Evidence: `smoke_process_transition_next_work_recommendation`, `smoke_existing_work_start_contract_compatible`, and `smoke_garage_work_start_session_bound.py` passed on 2026-09-03.
