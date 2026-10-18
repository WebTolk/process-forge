# T10 test report

Product verdict: **PASS with separate historical live-journal finding**. Raw commands/stdout/stderr/timings and exact current source hashes: [assurance-results.json](assurance-results.json).

- New monitor smoke: PASS in source and copied public fixture. Seven test groups cover truth/privacy/no-write, invalid/oversize/stale/races, lifecycle, bounded network, screen state/Unicode/control injection, cleanup and real CLI modes.
- Seven existing regression scripts: PASS (singleton/orphan, status/version, scheduler isolation, neutral core, no manual infrastructure, host-owned MCP, optional hooks).
- Public cleanliness, checksum inventory, Python AST and changed-doc links, git diff --check: PASS.
- 991-file normalized public fixture: schema and checksum checks PASS; new monitor smoke PASS. It is a private validation input, not an installable release archive.
- Preservation: original 3769-file baseline unchanged outside nine allowed product files; no unexpected product additions. Previous dirty changes and frozen evidence remain intact.
- Actual Windows PTY: [Q exit transcript](windows-pty.json), [Ctrl+C transcript and wrapper boundary](windows-ctrl-c.json). Live viewer observed the same existing owner PID before and after exits; no server lifecycle command was issued. Freshness/health transitions are visible. Source viewer against installed state does not prove installed CLI delivery.

One full-checkout schema invocation remains FAIL: .pf/runtime/events/events.ndjson:34212, Extra data. Raw line SHA256 6f1fa1694252d1b08e1ac8351716ab6129f302a26135c6bd56d7b1466c088739; embedded time and adjacent events are 2026-09-26T12:15, before T10. Line preserved, root cause uninvestigated, no journal repair. The expected-failure assertion in assurance.py checks the same specific failure and never converts the validator's exit code 1 into a claimed schema PASS.

No browser/UI-web test applies to this terminal feature. Shared install/restart/public release are not_applicable to scoped source delivery. Full historical journal health and all future T10 proposal features remain outside this acceptance. Current Windows run does not assert native POSIX execution.

Gate decision: scoped implementation and regression assurance complete; internal source delivery may proceed with the explicitly retained journal finding and deployment boundary. General project/release readiness is not inferred from that decision.
