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
  objective. The agent provides meaning; ProcessForge selects or validates the
  process stage, run id, task id, assignment id, timestamps, and technical
  links.
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
7. complete work through ProcessForge artifacts, reviews, logs, and handoffs.
