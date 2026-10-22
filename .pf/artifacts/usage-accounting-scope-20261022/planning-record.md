# Уточнение границ учёта PF

2026-10-22. Запрос оператора: тарифы и денежные потоки не относятся к ответственности PF; PF только учитывает данные. Вопрос по хранению: проектные базы, одна общая с project_id или проектные плюс общая для отчётов.

## Orchestration / task record / execution context

Новый документационный Work после завершённого planning cycle, не возобновление terminal Work. Run: `garage-usage-accounting-scope-20261022-planning-only-amendment-to-comple`; assignment: `usage-accounting-scope-20261022-planning-only-amendment-to-completed-tok`; context: `usage-accounting-scope-20261022-planning-only-amendment-to-completed-tok-capsule`, checksum `sha256:2aeabb23c053776d608c7380d4b9a0343d6e6dfcc9dcddb674c0c9a614c67ec6`. Live project context fresh/continue. Assignment/capsule checked; read/write_artifact only, write_product forbidden, subagents forbidden. Lifecycle software-feature-development@1.2.1 applies to documentation only.

## Intake / brief / scope

Required result: authoritative scope-amendment.md, added as first required immutable input on the existing open planning_only token task. Preserve approved old plan/evidence bytes. Financial functionality is excluded by operator instruction. Storage choice remains an architectural recommendation for discussion; no database/code created. No service, install, restart, product tests or new implementation.

## Investigation / impact

Read `.pf/AGENTS.md`, `.pf/process-forge.yaml`, original token card and the sealed implementation-plan.md from usage-cost-planning-20261022. It already proposes one durable workplace SQLite for accounting facts, separate from project lifecycle files. Financial parts to supersede: RateCard/Valuation, valuation.py, pricing and currency tables, reported/estimated monetary totals, financial query/export fields, valuation block and A15–A17 acceptance scenarios. Original token card objective has no money requirement, so it needs only an amendment input, not a lifecycle or grant change.

This is a few-file documentation correction; known non-code files were read directly. No structural code mapping/refactoring is involved. Existing unrelated source/docs diff inventory and staged-empty state recorded before writes. Sealed previous planning directory will be hash-compared to HEAD; product diff will be compared before/after.

## Domain / rules

Retained domain: actual token UsageRecord, observed ActivityInterval, exact project/run/assignment/attempt/source/agent/model identity, status, source quality, provenance, deduplication/revisions and statistical aggregation. Exclude tariffs, monetary valuation, billing, payments, subscription allocation, currency arithmetic and monetary DTOs from this feature. Raw private provider logs follow existing retention policy and are not promoted to a financial contract.

Data ownership: one authoritative copy of normalized usage facts; project/task reports are projections. Project id is stable and namespaced within workplace; project path/display name is not an identity. A consumer's project scope constrains queries even when rows share one file. Store placement is infrastructure; domain and collectors do not depend on physical DB path. Optional future remote replication uses original record identities and does not turn a summary into another additive fact.

Next: document the storage alternatives, recommendation and explicit portability tradeoff; append the immutable input; self-review and documentation-only validation; commit both remotes, close native lifecycle and stop.
