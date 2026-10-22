# Planning assurance and review

2026-10-22. Review type: **primary self-review**, not independent review. The immutable planning capsule forbids subagents. No product implementation or real accounting receipt capture was performed; acceptance scenarios describe future verification.

## Review findings resolved in the design

- Context size could be confused with expenditure: separated PreCompact/PostCompact context metrics from usage; modern installed Kimi Code2.3.0 is distinct from Python Kimi CLI. Source addendum preserves the initial sealed inventory and records the correction.
- Modern Kimi session-scoped usage could be silently lost by a generic cumulative-summary filter: checked installed program bundle and official source; semantics must be qualified per version/record type, not guessed from scope name.
- Main interactive agent could be omitted while counting only native workers: first implementation gate explicitly covers interactive clients, known unsupported channels and honest coverage. Plugin read access does not prove a token source.
- Request receipts, parent/child mirrors and session summaries could duplicate expenditure: one proven contribution/coverage, source revisions/conflict and transactional cursor rules. Identical distinct real requests must not collapse by payload hash alone.
- Presence/worker/request durations could inflate time: separate execution from session presence, union nested intervals, aggregate agent minutes separately from occupied project time. Unknown crash tails remain partial.
- API price could be presented as subscription spend or both cost bases added: separate reported cost and tariff estimate; immutable rates/valuation revisions; no guessed hidden model, FX or automatic subscription allocation.
- One local store per UI or compulsory server could complicate future development: one neutral module/SQLite and shared queries; future TUI/plugin/REST remain adapters. File-only operation remains available.
- Unknown attribution/SDK zero defaults could fabricate task totals: explicit project-unassigned/missing/partial and exact Work/attempt binding. Future privacy/export permissions do not follow from statistics access.

No unresolved blocker to delivering the **plan**. Source/version/real-receipt, compaction/retry, storage ownership and future plugin/transport capability questions are explicit implementation gates; they are not claimed to be resolved runtime behavior.

## Test plan and cases

[acceptance-scenarios.md](acceptance-scenarios.md) contains22 future scenarios. Planning checker independently recomputes representative token, revision/cumulative and interval arithmetic and a fictional Decimal tariff example. This checks specification consistency, not implemented accounting correctness.

Commands and results (Python3.14.3, PyYAML6.0.3, Git2.53.0.windows.2):

- `python .pf/tmp/usage-cost-planning-20261022/check_plan.py` — exit0. Original card is exactly HEAD plus one immutable input, remains open/planning_only/writer=false; five local links resolve at that checkpoint;9 named reference scenarios checked, including A15=0.0027USD with fictional rates. Private evidence: document-check.json with file hashes.
- `python bin/pf.py run-doctor --project-root . --run garage-usage-cost-planning-20261022-planning-only-for-existing-pf-task-t` — exit0 at in-progress assurance; run schema, identity, task index and no private absolute path checks pass. Final completed-state doctor is a separate delivery check.
- `git diff --check -- <task artifacts/log/original card>` — exit0. Original card diff exactly4 inserted lines; index empty before task staging.
- Live `pf.context` recheck — fresh `ctx-20261021-162229-c46ea2`, continue after input reference update. No refresh/restart.

Preservation inventory/check is retained privately: source/docs use streaming SHA-256; unrelated historical dirty files use size/mtime signatures, not a claim of full byte hashing of97k files. Task-native PF records and the explicitly allowed original card input change are excluded from unrelated-change comparison. Final result is recorded in the delivery log.

## Code quality applicability

Product Python/tests/public docs and runtime configs were not edited. Therefore product unit/smoke suites, Ruff/Black/Pylint/mypy/complexity checks and archive/install/connected-host qualification are **not applicable to this document-only change**. Task-local private check scripts are disposable verification aids, not shipped product code. YAML parse/exact semantic comparison, link and arithmetic checks, whitespace, native Work validation and run doctor are the relevant assurance. Future implementation must run all applicable Python gates and real source qualification; this plan does not waive them.

Next: deliver exactly task documents, metadata reference and native planning records; verify both remote dev SHAs; finish the planning lifecycle and stop.
