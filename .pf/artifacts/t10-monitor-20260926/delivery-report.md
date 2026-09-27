# T10: source delivery

Decision: **ready for internal source use, with documented project-journal finding**. First bounded monitor slice is implemented and tested. The complete historical T10 proposal is not declared finished.

Operator entry point from this checkout:

```powershell
python -B tools/processforge.py monitor --workplace D:/.agents/processforge-workplace
python -B tools/processforge.py monitor --workplace D:/.agents/processforge-workplace --once --ascii
python -B tools/processforge.py monitor --workplace D:/.agents/processforge-workplace --json
```

Use an interactive terminal with VT support; TERM=dumb deliberately produces a single snapshot. Q/Esc/Ctrl+C close only the viewer. The live environment's host cache exceeds the 1 MiB ceiling, so registered counts currently display unknown/cache_oversize. Other absent activity aggregates are unknown by contract. This is useful status with explicit coverage, not a promise that all proposed metrics are available.

Delivery contents: nine declared product files, EN/RU [operator guide](../../../docs/concepts/runtime-monitor.md), [Russian guide](../../../docs/ru/concepts/runtime-monitor.md), new release-test smoke entry and refreshed public inventory. Prior dirty source work retained. Source hashes and 991-file normalized validation fixture recorded in [assurance-results.json](assurance-results.json).

Validation: source/new/existing regression tests, public-only schemas/checksums/new smoke, AST/links/cleanliness/diff/preservation and actual Windows PTY observations. Detailed limits: [test-report](test-report.md). Full-checkout schemas retain the old malformed event-line FAIL; no global-green or official-release claim.

Delivery profile: **source validation profile run** (fixture schema/checksum/smoke). Release archive/build/installed update/publication: **not_applicable — not requested in this scoped viewer implementation**. The fixture is explicitly not an installable release archive. Installed Core remains unchanged, so its CLI may not recognize monitor; use source command above until a separately prepared update. No Runtime/MCP/hooks/Ledger restart or configuration mutation occurred.

Handoff to evolve: record next bounded activity-aggregate scope and independent journal investigation; complete current Work and verify all stage hashes/capsule/source checksums. Preserve .pf/tmp/t10-monitor-20260926/public-fixture as declared private qualification evidence; no cleanup of old T06 paths.
