# Fresh-Session Continuation Acceptance

Status: passed

The continuation contract accepts a newly issued `pf.work.start` with an explicit allowed process and does not require a session manager or runtime service. The created Work has a new run ID and an isolated capsule.

Evidence: `smoke_existing_work_start_contract_compatible`, `smoke_multi_process_garage_sessionless`, and `smoke_garage_work_start_sessionless.py` passed on 2026-09-03.
