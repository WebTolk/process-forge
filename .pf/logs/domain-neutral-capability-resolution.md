## 2026-07-29 17:51 - implementation

Task:
Execute `задания/processforge_domain_neutral_capability_resolution_master_prompt.md`.

Files changed:
Runtime resolver, specialization schema, smoke helpers, new domain-neutral
smokes, docs, checksum inventory, and release archive outputs.

Artifacts changed:
- `.pf/artifacts/domain-neutral-capability-resolution-report.md`
- `.pf/reviews/domain-neutral-capability-resolution-review.md`
- `.pf/handoffs/domain-neutral-capability-resolution-handoff.md`

Templates used:
Project-local `.pf` report/review/handoff conventions.

Tools used:
PowerShell, Serena fallback search, `apply_patch`, ProcessForge release gates.

Decisions:
Removed builtin user capability satisfaction. Kept PF internal runtime
operations separate from user process capabilities. Made resource-profile-only
context resolution avoid an implicit workflow process in smoke helpers.

Risks:
Existing built-in process definitions may still declare capabilities as process
data; this is now visible as `needs_resources` unless active resources provide
the IDs.

Next steps:
Commit only after reviewing the combined uncommitted slices.

Handoff:
See `.pf/handoffs/domain-neutral-capability-resolution-handoff.md`.
