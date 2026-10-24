# DB storage topology clarification

## 2026-10-24 primary / operator clarification

Task: Capture confirmed workplace/project SQL topology for the existing DB backlog.
Analyzed: current context, original read-only planning card/spec/research, admitted amendment assignment/capsule, operator's subsequent search/RAG clarification.
Status: original amendment is at orchestration; no product or database mutations and no requirements artifact published.
Decision: mandatory search-in-main-SQL text was an assistant assumption, withdrawn after the operator left this question open. Preserve accounting/operations in SQL and future adapter support. Search indexing/storage and future RAG need separate consideration.
Artifacts: scope-change-handoff.md records the changed requirement; original inputs and capsule remain unchanged.
Next: governed cancellation and bounded successor for requirements plus primary-source research; no implementation, new DB, migration, maintenance, service action or agent scheduler work.

## 2026-10-24 primary / revised requirements and research

Task: Record confirmed SQL topology while keeping search placement undecided.
Artifacts: requirements.md, research.md, report.md, current-requirements.json and document validation.
Status: scoped planning-only successor valid/ready, exact predecessor binding retained; old initial Work cancelled. Original DB task/spec/research/card and both capsules unchanged. No duplicate implementation task or RAG/scheduler work registered.
Research: local usage-accounting/resource-search-index documents first; official SQLite isolation/WAL/FTS5 pages verified. Same-file writes are serialized, WAL does not add concurrent writers; FTS maintenance may compete. Separate retrieval storage is a recommendation pending measurements, not an approved physical topology.
Tooling: first successor request with an artifact path in predecessor_handoff was rejected work_scope_invalid; current contract requires .pf/handoffs for that optional field. Preserved the artifact as a pinned source and used supported exact predecessor binding without editing capsules or broadening old scope.
Validation: JSON, revision hashes, relative links, whitespace, explicit undecided-search flags and original input/index hashes passed. Product pytest/Ruff/mypy not applicable to this document-only change. No benchmark, migration, DB creation, configuration or infrastructure action.
Next: native lifecycle recording and mirrored evidence delivery.

2026-10-24T04:40:35.966222+00:00 | primary | Requirements-only successor run_completed; native run/capsule doctors21/12 PASS. SQL workplace/project topology recorded, search physical placement undecided, future RAG separate. Original inputs/index preserved. Publishing scoped documents through isolated Git index; both live dev parents match, GitVerse TOKEN helper enforced.

2026-10-24T04:40:47.947069+00:00 | primary | Requirements commit 2a9778a5501939b6421e214fcbcf3eb4168afb57 published in parallel and read back exactly from both origin/dev and gitverse/dev using TOKEN. Final accounting records this receipt/log only; implementation remains unstarted, search physical placement undecided and protected original inputs/index preserved.
