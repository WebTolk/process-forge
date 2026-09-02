# Garage Core

Garage Core is the read-first ProcessForge layer for a project that already has
a `.pf` context. It lets an agent understand the project, search approved local
knowledge, and resolve selected resources before any governed work, Runtime
session, hook replay, chat transcript, Director, or multi-agent lease exists.

## Levels

Level 1, Garage essentials:

- `pf.context` reads project identity, context freshness, selected process,
  authorized resources, search readiness, and active work summary.
- `pf.search` searches only resources authorized by the project snapshot.
- `pf.resolve` resolves a selected resource id from the same snapshot.
- Snapshot, local search index, resource manifests, templates, process metadata,
  and tool metadata are sufficient inputs.

Level 2, governed work:

- `pf.work.start` starts or continues governed work from a high-level
  objective. ProcessForge selects the initial stage and pins the effective
  Process definition, version, fingerprint, context snapshot, and assignment
  capsule.
- `pf.work.state` returns the current stage, required inputs, obligations,
  artifacts, gates, blockers, and allowed outcomes.
- `pf.work.transition` accepts an outcome and evidence. ProcessForge resolves
  the next stage from YAML, updates the Assignment, emits stage events, and
  completes the Run after the final stage.
- run, task, assignment, capsule, artifact, review, log, and handoff files define
  durable work.
- agents start or continue governed work after they understand context and need
  to change files or produce delivery evidence.

Level 3, Forge orchestration:

- Runtime, Agent Ledger, hooks, session presence, heartbeat, chat, Director, and
  multi-agent coordination add orchestration and telemetry.
- these systems can enrich context and enforce live coordination, but they are
  not prerequisites for Level 1 context/search/resolve.

## Session Boundary

`project_root` is the authority for Garage reads. A supplied session id is
validated against Agent Ledger and must match the same project. The session is
reported as `session.status: bound`, but it does not promote Garage to Forge.
Forge mode follows the project/runtime coordination model, such as organized
Director-required coordination. Session-scoped views remain available through
`pf.session_context`, `pf.session_chat`, and `pf.session_activity`.

Session-scoped tools remain session-scoped. Garage tools do not read raw
provider payloads, do not create production sessions, and do not use a session as
the authorization source for resources.

## Search Readiness

Garage search reports one of four readiness states:

- `ready`: snapshot and index are fresh and indexed documents exist.
- `empty`: the search infrastructure is fresh but the authorized corpus has no
  indexed documents.
- `stale`: the index needs maintenance before trustworthy results.
- `blocked`: the project context or search setup is broken.

MCP may run bounded technical maintenance before a query when the index is
missing or stale. The search itself remains a pure query against the
snapshot-authorized index. Semantic changes, resource selection changes, or
unclear context updates require operator decision through the normal project
context flow.

## Resource Policy

Real article/documentation resources can opt into fulltext indexing. Large
source trees and SDK mirrors default to metadata navigation unless their
resource manifests explicitly select a small fulltext subset. Search never
falls back to workspace-wide file scanning, private home directories, web
search, or unselected workplace resources.

Project context separates the diagnostic `available_knowledge_resources`
catalog from the selected resource set. Only selected resources are copied to
`local_search_resources`, may be resolved by `pf.resolve`, and may contribute
to `pf.search`. A snapshot records `resource_selection` with the selection
mode, target platform versions, counts, and selector provenance.

Use `context_requirements.resource_selection.platform_versions` for a
data-driven platform target and explicit `knowledge_resources` selectors for
an override. A selector may use `id`, `preferred_version`, and `constraint`.
Older manifests without selectors use the narrow migration mode: direct
platform packages plus the newest compatible version of each logical resource.
For that migration only, selected documentation with a legacy metadata policy
is indexed as bounded text documentation; source-tree and symbol policies stay
metadata-only.

## Agent Path

The default agent path is:

1. read `.pf/AGENTS.md`;
2. call `pf.context` with `project_root`, or read the snapshot when MCP is
   unavailable;
3. use `pf.search` for authorized project knowledge, templates, process, and
   tool metadata;
4. use `pf.resolve` before opening a resource root;
5. perform local read-only analysis;
6. call `pf.work.start` with the substantive objective;
7. call `pf.work.state`, satisfy the current obligations, and call
   `pf.work.transition` with outcome and evidence;
8. repeat until `action: run_completed`.
