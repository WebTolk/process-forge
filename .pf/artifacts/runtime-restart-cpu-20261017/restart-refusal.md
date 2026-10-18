# Managed restart refusal

The normal installed `server restart` was attempted twice and returned HTTP 409 `runtime_busy_or_activity_unknown`. Runtime remains PID 13540 / instance 84c60b0dd3df4740aaf1f18d3e9cce2c and ready/degraded; no restart is claimed.

The actual installed fresh shutdown-worker reader uses a 0.5-second budget. It returned partial coverage, `counts.running=null`, observed running=0, issues budget/coverage. An OS process-name/command query found no visible PF executor processes, but this does not turn unknown into zero. No force flag or OS kill was used.

The operator has been asked specifically whether to allow managed `server restart --force` for this existing Runtime. This question is caused by the actual service refusal, not an additional source-update approval rule. Dependent restart actions wait for that answer; read-only diagnosis and the 30-second baseline are retained.
