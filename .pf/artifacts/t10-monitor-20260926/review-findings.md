# T10 review

Result: **pass_with_conditions for source delivery**. Primary-agent review after implementation, single-agent process; no independent reviewer claimed. No open blocking defect in the bounded viewer scope. Public release and shared installation are not qualified by this review.

Reviewed own delta against originals rather than attributing all pre-existing dirty changes to T10. CLI changes are one smoke entry, wrapper, parser section and logger bypass. service change extracts existing lifecycle branches without changing the existing caller's observations; singleton/orphan and status regressions pass. Other initial product changes and prior artifacts are unchanged outside the declared scope.

Read-only review: collector reads known bounded paths and one GET /readyz; no load_token, /status, project scan, host mutation, logger construction or daemon lifecycle call. Numeric loopback validation, total probe deadline including trickle, response ceilings and no redirects/proxy/token are covered by real socket tests. PID query is bounded; filesystem availability remains a storage assumption.

Truth review: ready != healthy, old/future/missing timestamps do not become fresh, owner changes and failed probes remain unknown. Host registrations are explicitly cached, never active counts. Missing aggregate coverage remains null. Saved scheduler results are not represented as a live scheduler-thread test. Instance version is separate from running CLI version.

Terminal review: allowlist projection and control-character neutralization, Unicode cell cropping, ASCII fallback, changed-row renderer and cleanup in finally. Independent screen-cell model verifies resize/shrink/cleared tails, not merely presence of strings. Actual Windows PTY with TERM=xterm-256color verifies redraw and Q exit 0. Ctrl+C restored the screen/cursor too; enclosing PowerShell tool returned 1, so that wrapper result is not reported as a Python exit-code assertion. Earlier TERM=dumb observation correctly used one-shot fallback.

Conditions/boundaries: real host cache exceeds 1 MiB, so registration counts are unknown; do not raise limits silently. POSIX cbreak branch is covered only when tests run on POSIX; current execution is Windows. The 991-file fixture validates normalized public source, not a release archive/installer. Old journal failure remains separately open; no full-green checkout claim. Timestamp attribution is based on the malformed line and adjacent events at 12:15, before this task, not an initial byte baseline of the entire changing journal. Root cause is not determined.

Follow-up T10 scope: bounded authoritative activity/metrics aggregate and coverage, then any explicitly scoped lifecycle/tray controls. Avoid turning cached session records into active-worker indicators merely to populate the screen.
