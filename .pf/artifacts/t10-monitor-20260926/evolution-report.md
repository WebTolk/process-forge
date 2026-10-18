# T10 evolution and next scope

Captured locally; shared instructions/processes and user memory unchanged.

1. A viewer must not call convenient status APIs without checking side effects and cost. Current /status recomputes project data and its token loader can write; the bounded reader/probe plus a shared pure lifecycle classifier avoids that dependency.
2. Registration counts and cached session records are not active Work/worker metrics. A future bounded aggregate needs source definitions, freshness/coverage and limits before rendering more numbers. Observed oversized host cache confirms why a viewer cannot simply deserialize everything indefinitely.
3. Readiness and saved health/freshness are separate. Actual Windows observations included ready with degraded health and ready with stale state; the UI preserves those distinctions.
4. Terminal acceptance needs cell-state/resize/cleared-tail tests and real PTY observations. TERM=dumb/non-TTY and non-UTF-8 are normal fallback modes, not reasons to force escape sequences into pipes.
5. Product validation and changing project journals are different surfaces. Preserve old journal FAIL evidence; do not repair immutable/history data or claim overall-green because a product fixture passed.

Recommended next T10 slice: define and implement a bounded authoritative metrics snapshot for observed sessions/workers/Work/leases/events, with timestamps, source coverage and cache limits. Consume it from monitor only once qualified; do not scan entire project trees each redraw. Monitor remains read-only; server controls, tray/pf-server executable and log-profile editing stay separate.

Independent follow-up: investigate malformed event row 34212 with preserved raw hash and producer context; select repair/recovery only after understanding provenance. Source-to-installed update and scoped Git/public release preparation remain separate delivery work. Remote web is still deferred per operator decision.

Current outcome: first T10 monitor slice complete for source use; no new daemon/required model dependency. Finish via actual PF outcome, then verify completed lifecycle/evidence hashes and write continuation handoff.
