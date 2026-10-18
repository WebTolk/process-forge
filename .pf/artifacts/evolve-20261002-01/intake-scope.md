# Intake And Scope: evolve-20261002-01

Brief:
- Fix `evolve-20261002-01`: Work creation must preflight execution mode and effective permissions before publishing durable Run, Assignment, or capsule.
- Expected user-visible outcome: failed creation returns a precise blocked result, while valid explicit planning/read-write-artifact scope succeeds.

Accepted scope:
- Product code: `src/processforge_core/process_execution.py`, `src/processforge_core/continuation.py`.
- Tests: `tools/smoke_work_start_scope.py`.
- Documentation: `docs/concepts/work-context.md`, `docs/ru/concepts/work-context.md` if the executable contract changes.
- Evidence: `.pf/artifacts/evolve-20261002-01/**`, `.pf/logs/evolve-20261002-01.md`, `.pf/reviews/evolve-20261002-01.md`, `.pf/handoffs/evolve-20261002-01.md`.

Out of scope:
- `tools/processforge.py` writes, because PF reported active writer overlap with `agent-entry-e01-e02-scoped`.
- Runtime, MCP host, Agent Ledger, installed Core updates, restarts, or publication.
- Broad cleanup of historical `.pf` state.

Acceptance criteria carried from backlog:
1. Implicit implementation without product write permission returns a precise refusal before Work publication.
2. Explicit planning/read-write-artifact scope succeeds without mutating existing capsules.
3. `read_only`, documentation/planning, implementation, empty grants, and contradictory denies are covered.
4. Retry after timeout is documented as identity verification, not blind duplicate creation.

Python knowledge source:
- PF-resolved `docs.python:root` at `D:\.agents\docs\python`.
- PF-resolved `docs.python-practices:root` at `D:\.agents\docs\python-practices`.
