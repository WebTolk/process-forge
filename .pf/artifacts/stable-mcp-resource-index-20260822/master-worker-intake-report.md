# Master Worker Intake Report

## Scope

Assignment `stable-mcp-resource-index-master-intake-20260822` was executed as planning-only intake. No product code inspection or edits were performed. Read scope was limited to the assignment capsule, `.pf/AGENTS.md`, `.pf/process-forge.yaml`, `.pf/contexts/project-context.snapshot.yaml`, and `задания/process-forge-stable-mcp-resource-index-master-prompt.md`.

## Intake Summary

The master prompt defines one integrated delivery stream:

1. Build a stable local Resource Catalog from existing PF registries/manifests.
2. Build one derived workplace-level SQLite FTS5 Search Index.
3. Keep Snapshot as the only authorization resolver.
4. Expose authorized search through MCP via `pf.search`, `pf.resolve`, and `pf.session_context`.
5. Add Runtime-owned maintenance for stale/dirty/incremental refresh.
6. Fix the known durable conversation replay race.
7. Prove the whole path with real installed PF MCP and Codex hook acceptance.
8. Update EN/RU docs and pass independent architecture/code reviews.

This is not a single implementation task. It should be decomposed into gated PF assignments with non-overlapping write scopes.

## Current Context Risks

- Snapshot health is `blocked` in the provided context snapshot.
- The selected resource profile reports unsatisfied `research` and `process_governance` capabilities for the `knowledge-package-improvement` process.
- No tools, MCP resources, templates, or workplace knowledge resources were granted to this worker.
- Current worker scope did not permit source, schema, tool, or docs inspection, so exact implementation file paths must be finalized by the first audit task.

These are not blockers for this planning report, but they are blockers for full implementation unless the orchestrator grants the relevant read/write scopes and resolves the process capability mismatch.

## Recommended Task Graph

### T0: Current-State Audit

Goal: establish the executable baseline before design or edits.

Inputs:
- Project `.pf` manifest and fresh/blocked context snapshot.
- Existing registries, packages, process catalog, MCP tools, Runtime scheduler, CLI, path-security code, SQLite/search code.

Outputs:
- `resource-catalog-index-current-state-audit.md`

Write scope:
- Audit artifact only.

Read scope:
- `.pf/**`
- registry/package/process files
- source files for resolver, snapshot producer, MCP tools, CLI, Runtime, path containment, current search/index logic
- schemas and tests relevant to those areas

Exit gate:
- Each searchable resource kind has canonical identity, registry source, root/reference, snapshot representation, searchable fields, and authorization boundary documented.

### T1: Architecture and Schema Design

Depends on: T0.

Goal: lock the design before product edits.

Outputs:
- `resource-search-index-design.md`
- `resource-search-index-schema.md`
- `index-maintenance-design.md`
- `full-mcp-acceptance-test-plan.md`

Write scope:
- Design/test-plan artifacts only.

Exit gates:
- Snapshot remains the only resolver.
- Catalog is not a second package/resolver system.
- One workplace-level index is selected.
- SQLite DB is private, derived, rebuildable, schema-versioned.
- FTS5 availability/degraded behavior is explicit.
- Runtime owns maintenance; MCP remains query adapter.

### T2: Resource Catalog and Snapshot Authorization Core

Depends on: T1.

Goal: implement Resource Catalog construction from existing PF registries/manifests and snapshot-filtered authorization primitives.

Expected implementation areas:
- Core catalog/read model service.
- Snapshot allowed-resource extraction.
- Path containment and registered external-root validation.
- Tests for snapshot filtering and traversal denial.

Write scope:
- Core service files for catalog/snapshot authorization.
- Relevant schemas if new internal derived-state records need validation.
- Focused tests.
- `resource-index-implementation-report.md`

Exit gates:
- Catalog entries are derived from existing PF sources.
- No absolute machine path is used as canonical identity.
- Search authorization can be computed from current session -> project -> fresh snapshot.
- External registered knowledge roots remain allowed only through registry.

### T3: SQLite FTS5 Search Index Core

Depends on: T2.

Goal: implement derived SQLite index, indexing policies, lifecycle states, and query API.

Expected implementation areas:
- SQLite schema creation and versioning.
- FTS5 capability probe.
- Index lifecycle: `missing`, `building`, `fresh`, `stale`, `degraded`, `failed`.
- Indexer for knowledge resources and templates.
- Optional tool metadata indexing or explicit deferral after audit.
- Incremental add/change/delete handling.
- Bounded text file reading, encoding policy, binary skip policy.
- Stable pagination and ranking.

Write scope:
- Core search/index service.
- Internal runtime state storage under workplace runtime conventions.
- Tests and fixtures.
- `resource-search-index-schema.md` update if implementation refines schema.
- `index-performance-baseline.md` draft with first local measurements.

Exit gates:
- `resources`, `documents`, `documents_fts`, and `index_state` equivalent structures exist.
- Index can be deleted and rebuilt.
- One corrupted file does not break rebuild.
- `limit + offset` ordering is stable and leak-free.
- Search during refresh does not falsely report fresh state.

### T4: CLI Parity

Depends on: T3.

Goal: expose operator diagnostics and maintenance commands using the same Core service.

Expected CLI commands:
- `search-index status`
- `search-index refresh`
- `search-index rebuild`
- `search-index doctor`

Write scope:
- CLI adapter only.
- CLI tests.
- Documentation notes for CLI.

Exit gates:
- CLI and MCP do not duplicate search semantics.
- Doctor reports schema version, SQLite/FTS5 capability, generation, counts, stale/failed counts, last refresh, and last reconciliation.

### T5: Runtime Maintenance

Depends on: T3.

Goal: make Runtime responsible for periodic and incremental index maintenance.

Expected implementation areas:
- Dirty/stale marking on registry/resource/context changes.
- Runtime scheduled refresh/reconciliation.
- Crash recovery after interrupted refresh.
- WAL/transaction/locking handling where needed.

Write scope:
- Runtime scheduler/maintenance adapter.
- Runtime tests.
- `runtime-index-maintenance-report.md`

Exit gates:
- MCP does not run daemon/background maintenance.
- No full scan on every MCP query.
- Add/change/delete are reflected after refresh.
- Interrupted refresh cannot leave index falsely fresh.

### T6: MCP Integration

Depends on: T3, T5.

Goal: expose stable session-aware search context.

Expected implementation areas:
- `pf.search`
- `pf.resolve` preservation/normalization
- `pf.session_context` search readiness block
- MCP response shaping and private/local reference boundaries

Write scope:
- MCP adapter files.
- MCP tests.
- Acceptance fixture wiring.

Exit gates:
- `pf.search` filters by current MCP session -> Ledger -> project -> fresh snapshot.
- Hidden fallback to whole workplace, home directory, other projects, Context7, or web is impossible.
- `pf.resolve` remains distinct from `pf.search`.
- `pf.session_context` returns compact search status plus process/stage obligations.

### T7: Conversation Race Remediation

Can run after T0/T1; must finish before final acceptance.

Goal: fix the proven durable race where `UserPromptSubmit` can be accepted raw before Ledger session materialization, leaving `pf.session_chat` empty.

Expected implementation areas:
- Durable deferred/replay-needed record.
- Deterministic replay after Ledger session availability.
- Deduplication for exactly-one chat message.
- Honest assistant final capture coverage based only on host-provided fields.

Write scope:
- Event/conversation projection logic.
- Ledger/chat tests.
- `conversation-ordering-remediation-report.md`

Exit gates:
- No in-memory-only correctness guarantee.
- User message appears exactly once.
- Assistant final capture reports explicit host limitation when unavailable.

### T8: Full Acceptance, Security, Performance

Depends on: T2-T7.

Goal: prove the complete user gate through real installed PF MCP.

Outputs:
- `full-mcp-acceptance-report.md`
- `mcp-security-review.md`
- `index-performance-baseline.md`
- `final-validation.md`

Required tests:
- Clean isolated workplace/project/Ledger/snapshot/knowledge/template/Runtime/MCP/hook fixture.
- Knowledge A/B visible, knowledge C invisible, template T visible.
- Missing -> build -> fresh lifecycle.
- Modify/add/delete refresh lifecycle.
- Crash/restart recovery.
- Pagination.
- Real corpus benchmark.
- Real Codex MCP: `pf.session_context -> pf.search -> local file read`.
- Live conversation replay.
- Process guidance through `pf.session_context`.
- Security matrix.
- Existing MCP/event/replay/init/worker regressions.
- Release/archive validation.
- `git diff --check`.

Exit gate:
- All Definition of Done items pass or are explicitly blocked with owner and remediation.

### T9: Documentation and Independent Reviews

Depends on: implementation readiness; reviews after T8 evidence is available.

Outputs:
- EN/RU docs updates.
- `independent-architecture-review.md`
- `independent-code-review.md`

Write scope:
- Public docs.
- Review artifacts.

Exit gates:
- Docs do not call lexical FTS “semantic search”.
- Architecture review PASS.
- Code review PASS.
- No private absolute paths in public artifacts.

## Artifact Map

Required artifacts from the master prompt:

- `resource-catalog-index-current-state-audit.md` — T0
- `resource-search-index-design.md` — T1
- `resource-search-index-schema.md` — T1/T3
- `index-maintenance-design.md` — T1
- `index-performance-baseline.md` — T3/T8
- `conversation-ordering-remediation-report.md` — T7
- `resource-index-implementation-report.md` — T2/T3/T6
- `runtime-index-maintenance-report.md` — T5
- `full-mcp-acceptance-test-plan.md` — T1
- `full-mcp-acceptance-report.md` — T8
- `mcp-security-review.md` — T8
- `independent-architecture-review.md` — T9
- `independent-code-review.md` — T9
- `final-validation.md` — T8/T9

Additional recommended PF artifacts:
- Assignment capsules per implementation task.
- Handoffs between core, runtime, MCP, conversation, docs, and review tasks.
- Focused logs for each worker if multiagent execution is used.
- Review requests before final validation.

## Write Scope Strategy

Use non-overlapping worker ownership:

- Audit/design worker: artifacts only.
- Core catalog/index worker: core search/catalog/index files and focused tests.
- Runtime worker: Runtime maintenance/scheduler files and Runtime tests.
- MCP worker: MCP adapter/session context/search response files and MCP tests.
- Conversation worker: Ledger/event/chat projection files and conversation tests.
- CLI worker: CLI command adapter and CLI tests.
- Docs worker: EN/RU docs only.
- Review workers: review artifacts only.

Avoid parallel writers on shared core files. If a shared service contract is needed, assign it to the core worker first, then let adapters depend on it.

## Quality Gates

Architecture gates:
- Snapshot remains the only authorization resolver.
- Catalog is derived from existing registries/manifests.
- SQLite index is derived, private, rebuildable, schema-versioned.
- One workplace-level index serves projects.
- Runtime owns background maintenance.
- MCP has no hidden global fallback.
- Tool metadata search does not grant tool authorization.
- Conversation correctness is durable, not RAM-only.

Security gates:
- Cross-project search denied.
- Unrelated workplace resource invisible.
- Registered external root allowed.
- Traversal denied.
- Arbitrary search root impossible.
- Cross-session chat denied.
- Raw payload not returned.
- Public artifacts contain no private absolute paths.
- Init/repair writes require explicit apply.

Functional gates:
- FTS5 probe reports capability.
- Degraded status is explicit when FTS5 is unavailable.
- Knowledge indexed.
- Templates indexed with snapshot provenance.
- Add/change/delete reflected after refresh.
- Crash recovery prevents falsely-fresh index.
- Stable pagination with total and no duplicates.
- `pf.session_context` includes compact search readiness and process obligations.
- `pf.resolve` remains distinct from `pf.search`.

Evidence gates:
- Clean fixture acceptance PASS.
- Real installed PF MCP acceptance PASS after host trust/approval.
- Live Codex conversation replay PASS for user message exactly once.
- Assistant final coverage honestly classified.
- Real corpus benchmark captured.
- Existing regressions PASS.
- Release/archive validation PASS.
- `git diff --check` PASS.
- Independent architecture and code reviews PASS.

## Blockers To Resolve Before Implementation

1. The provided snapshot is marked `blocked`; orchestrator should refresh or explicitly accept a pinned capsule for implementation.
2. `research` and `process_governance` capabilities are unsatisfied for the selected process route; orchestrator should select/update a specialization or override route before design/audit work.
3. This worker did not have source/tool/schema/docs read access; T0 must receive broader read scope.
4. No MCP/tools/workplace resources were granted here; real MCP acceptance requires host trust/approval and explicit runtime access.
5. Exact product file ownership cannot be assigned safely until T0 maps the current codebase.

## Recommended First Implementation Slice

Do not start with MCP or Runtime.

First slice should be T0 + T1 only:

1. Audit current resolver, snapshot, registries, search, MCP, Runtime, CLI, and path-security state.
2. Produce the design, schema, maintenance design, and full acceptance test plan.
3. Run architecture review on the design before product code edits.

Reason: the master prompt explicitly forbids creating a second resolver and requires preserving existing PF boundaries. A code-first slice risks duplicating resolver/search semantics before the current implementation surface is known.

After T0/T1 review passes, the first code slice should be T2 + a minimal T3 vertical path:

- Catalog from existing registries for knowledge resources only.
- Snapshot authorization filter.
- SQLite FTS5 build/rebuild/status for knowledge documents.
- One focused test proving authorized A visible and unauthorized C invisible.

Then add templates, Runtime maintenance, MCP adapter, conversation replay, and full acceptance in later gated slices.