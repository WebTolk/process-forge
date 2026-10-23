# Resource Search Index

ProcessForge local search has three separate boundaries:

- versioned workplace resources declare what may be indexed;
- the workplace SQLite FTS5 index stores derived resource documents;
- the project context snapshot authorizes which resource ids a session may query.

Projects do not own search documents. They only carry allowed resource
identities and fingerprints in the snapshot. The private derived DB lives under:

```text
<workplace>/runtime/search/local-resource-search.sqlite
```

This SQLite FTS5 store belongs to the workplace, outside project checkouts,
installed Core and public knowledge/release packages. It can contain private
document text. A shared physical store does not grant a project or Work access
to other resources; authorization filters still apply before results, counts
and ranking are returned.

`pf.search` is a query adapter. It does not fall back to the full workplace,
other projects, home directories, Context7, the web, or a hidden `rg` pass over
large source trees.

Each result contains a stable `document_id`, `resource_id`, canonical relative
locator, provenance, and `match_reason` (`content` or `metadata`). The locator
is meaningful only while its snapshot remains current; agents use `pf.resolve`
for authorized private navigation rather than reconstructing resource roots.

## Indexing Policy

Resources use one reusable contract:

```yaml
indexing:
  enabled: true
  mode: fulltext # fulltext | metadata | none
  fields:
    - title
    - description
    - tags
  sources:
    - path: articles
      mode: fulltext
      include:
        - "**/*.md"
      exclude:
        - drafts/**
    - path: core/6.1.2
      mode: metadata
      role: source_tree
```

`fulltext` stores metadata plus selected text files in FTS. `metadata` stores
identity, title, description, version, root/path reference, and declared
metadata only. `none` excludes the resource from local search.

Large source trees, SDK mirrors, vendor trees, and multi-version platform
snapshots should use `metadata` unless their manifest explicitly selects a
small fulltext source. Search can return a navigation root, but Codex should use
normal filesystem reads and `rg` inside the selected root when it needs source
code detail.

## SQLite Model

The derived DB schema is resource-oriented:

```text
resources
documents
documents_fts
index_state
```

`resources` tracks `resource_id`, `resource_type`, `version`, `fingerprint`,
`indexing_policy_hash`, `root_ref`, and refresh status. `documents` tracks
`resource_id`, `relative_path`, `kind`, `title`, hashes, and JSON metadata.
`documents_fts` stores searchable fulltext fields. `index_state` stores the
Workplace catalogue state and project snapshot scopes in the same shared DB.
Project snapshots authorize resource ids per query; documents are not duplicated
for each project.

The stored resource fingerprint also binds the complete resolved root set, even
when a fulltext root contains no documents. Verified status and selected metadata
projection detect root remapping without opening unselected document bodies.

## CLI

The explicit workplace operation requires a workplace target and `--apply`:

```bash
python bin/pf.py search-index-maintain --workplace <workplace> --apply --json
```

It uses the live registered workplace catalogue without enumerating projects.
Its schema-version-1 result has kind `pf.search_index.maintenance`, workplace
scope, `project_count: 0`, `results` and a relative `report` reference. Success
returns exit code 0; refusal or failure returns a nonzero code. Omitting `--apply`
refuses before creating the maintenance service. Project context and project
Work grants do not authorize maintenance of the workplace; the caller needs
separate authorization for that scope.

Existing commands with a project scope retain their options:

```bash
python bin/pf.py search-index status --project-root <project> --workplace <workplace>
python bin/pf.py search-index refresh --project-root <project> --workplace <workplace>
python bin/pf.py search-index rebuild --project-root <project> --workplace <workplace>
python bin/pf.py search-index doctor --project-root <project> --workplace <workplace>
python bin/pf.py search-index tick --project-root <project> --workplace <workplace>
```

These project-scoped commands require a project root and read its context snapshot. `status`
is read-only; `status --verify-files` checks authorized file fingerprints and
reports stale state when their content changed. `refresh` indexes resources
authorized by that snapshot, respecting `indexing.mode`. `rebuild` deletes the
derived DB and builds it again; `tick` performs one bounded pass for the project
snapshot scope.

`refresh`, `rebuild`, and `tick` require context status `fresh` or
`fresh_with_updates`; otherwise they refuse with exit code 1. `status` and
`doctor` remain available for other context states. `doctor` reports project
context freshness as `PASS` for these two states and `WARN` otherwise. The three
explicit mutating commands delegate to the same maintenance owner through
`run_scoped`; they do not load the workplace catalogue or acquire a broader
source scope. Legacy `rebuild` retains its existing shared-DB replacement
behavior, rebuilding from the supplied project selection.

## Batch Knowledge Addition

`knowledge-add-batch` accepts a YAML envelope with `schema_version: 1` and a
`resources` list in the existing `knowledge-add-resource` record format:

```yaml
schema_version: 1
resources:
  - id: example-guide
    kind: article
    title: Example guide
    description: A registered reference
    source:
      type: url
      url: https://example.org/guide
    license:
      name: unknown
```

```bash
python bin/pf.py knowledge-add-batch --workplace <workplace> --package <package> --batch-file batch.yaml --dry-run --json
python bin/pf.py knowledge-add-batch --workplace <workplace> --package <package> --batch-file batch.yaml --apply --json
```

The package must already exist. Default/dry-run performs no writes or indexing.
Each applied record uses the existing manifest/resource-index/private-registry
transaction and audit/recovery mechanism. Ordinary per-item errors are reported
in input order and processing continues. Only successfully completed resource IDs
are sent once, after the batch, to `WorkplaceIndexMaintenanceService.run_resources`.
It narrows the live registered catalogue, retains other SQLite rows and reads no
unselected document bodies. No URL content is downloaded. Partial addition or
indexing failure produces a nonzero exit; indexing failure preserves additions.

A successful targeted pass attests only to that selection. It acknowledges known
pending changes only when all of them belong to its successful IDs, with no prior
failure or concurrent change. The backend updates catalogue metadata from stored
rows only when all registered identities/policies still match, without reading
unselected bodies. This lets a clean batch resume search. Unknown/unselected
changes, missing coverage or previous failures keep global search unavailable
until the appropriate explicit maintenance. A partial pass preserves the previous
full-reconciliation timestamp. Future scheduled reconciliation uses the same
owner; periodic scheduling is not part of alpha4.

## Runtime And MCP

The physical Workplace catalogue is read by the concrete Core
`WorkplaceSearchCatalogReader`. It reads current registries, registered package
roots, active official knowledge packages and templates, then resolves their
path references. It requires no project context, CLI, Runtime, Ledger or session.
Maintenance and bounded session search-status projection use this reader directly;
the historical catalogue functions in the monolith delegate to it. This catalogue
does not grant a project permission to query any resource: project-scoped CLI/MCP
authorization and freshness checks still apply.

`WorkplaceIndexMaintenanceService` owns explicit index execution, serialization,
durable state and recovery, reusing the existing `ResourceSearchIndex` engine.
The workplace CLI calls `run`; existing scoped refresh/rebuild/tick commands
call `run_scoped`. A cold `IndexMaintenanceJob.execute()` calls the same `run`
operation when explicitly invoked. Alpha4 registers no Runtime search job,
thread, loop, timer or autostart. Periodic invocation belongs to the future PF
scheduler and is not delivered here.

Project initialization, refresh, repair, context reads and project search only
observe the existing index. They do not build, queue or wait for maintenance.
PF-owned resource registration and update/rollback paths can mark existing
derived state dirty; they leave reconciliation for explicit maintenance.
Observation does not verify document bodies. External file changes are detected
by explicit `status --verify-files`, verified `tick` or workplace maintenance.

Only one explicit writer may operate on a workplace at a time. A competing
writer receives a bounded busy refusal. The OS-owned lock is released on process
death; the durable `running` record remains incomplete until a subsequent
authorized workplace pass recovers it. Failed or interrupted maintenance is not
reported as fresh, and a project-scoped pass cannot clear incomplete workplace
maintenance. State and history live under `runtime/search/maintenance-state.json`
and `runtime/search/maintenance-history/`; the latest maintenance report is
`runtime/search/latest-maintenance.yaml`. These are private derived/operational
files, not public knowledge artifacts.

Private pending records in `runtime/search/invalidation-notifications/` bind
notification identities to selected resource IDs or an unknown change. Only exact
captured notifications acknowledged by a successful pass are retired while the
durable guard is still running. A failed token write remains visible through the
pending notification; readers inspect names/metadata and never source bodies.

`pf.search` never reports known stale data as `fresh`. If the index is missing,
stale, building or degraded, the result carries that `search_status` and returns no matches
until maintenance refreshes the derived DB.

Context freshness, required-resource readiness, physical search availability and
authorized coverage are independent observations. A ready context may have no
search index; a fresh physical index may have no documents authorized for a
particular project. `pf.work.search` retains its separate verified-material
path with pinned/current/stage access and material checks; workplace maintenance
does not widen it or replace its live verification.

Index freshness is not the same as semantic corpus readiness. A project can
have a fresh SQLite/FTS index with zero authorized resources or zero indexed
documents. Garage readiness checks should therefore show both infrastructure
state and corpus state: snapshot freshness, SQLite/FTS availability, index
freshness, authorized resource count, and indexed document count.

`pf.search` requires a project root, fresh resource resolution, fresh index
state, and resources authorized by that project's snapshot. It does not require
a Ledger session, hooks, daemon, write access, browser automation, CI,
deployment, or any other capability that is unrelated to the read-only query.
When a session id is supplied, MCP verifies that the session is bound to the
same project and then treats the session as an enhancement, not as the
authorization source. For example:

```text
Joomla resources fresh
filesystem.write missing
-> pf.search works
-> write-dependent action remains blocked
```

`pf.session_context` exposes compact readiness:

```yaml
context_freshness:
  status: fresh
resource_readiness:
  status: fresh
execution_readiness:
  status: blocked
search:
  status: fresh
  generation: <index-generation>
  stale: false
```

Resolved local paths are request-local runtime data. Public snapshots and
artifacts keep `path_ref` references instead of private absolute paths.

## Backend And Future Storage Boundaries

SQLite FTS5 is the only delivered backend and supplies lexical fulltext search.
The narrow `ResourceIndexBackend` port describes the operations actually used
by maintenance: `refresh`, `rebuild` and `maintenance_tick`. It separates search
backend execution from the shared application component; it is not a database
connection API, ORM or another indexing algorithm.

A future shared DAL and named connection profiles would own connections,
transactions and credentials. A later MySQL/MariaDB/PostgreSQL search adapter
would need its own conformance tests for tokenization, ranking, access filters,
atomicity and recovery; a SQL driver alone does not provide that equivalence.
Vector/hybrid retrieval would additionally require explicit chunking, embedding
model/version/dimensions, generation identity and update/delete behavior. RAG is
the retrieve/augment/generate application pipeline, not a database driver.
These adapters, embeddings, RAG and the general scheduler are future work;
alpha4 does not provide or silently activate them.
