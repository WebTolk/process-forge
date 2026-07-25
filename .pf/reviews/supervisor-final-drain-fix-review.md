# Supervisor Final Drain Fix Review

- scope reviewed: final drain loop, no-start drain mode, durable `exit.json` handling, failed worker lifecycle sync, and new regression smoke
- finding: no report-artifact success fallback remains in the touched supervisor path
- finding: final drain is bounded by `--final-drain-timeout` or a derived timeout capped at 5 seconds
- finding: final drain uses `start_allowed=False`, and `tools/smoke_supervisor_final_drain.py` verifies a newly unblocked dependent task is not started during drain
- finding: non-zero `exit.json` is preserved as failed runtime state and synchronized to task/run lifecycle as `failed`
- finding: lost PID without `exit.json` is confirmed across observations before `unknown_exit`, reducing Windows PID visibility flakiness while preserving the no-report-success rule
- residual risk: very long-running detached workers can remain `running` when final drain timeout expires; this is intentional bounded behavior and is reported as pending rather than forced to completed
- verification reviewed: targeted supervisor/runtime smokes passed before full release validation
- status: approved for release-test and archive validation
