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
current project snapshot authorization state without duplicating documents per
project.

## CLI

```bash
python bin/pf.py search-index status --project-root <project> --workplace <workplace>
python bin/pf.py search-index refresh --project-root <project> --workplace <workplace>
python bin/pf.py search-index rebuild --project-root <project> --workplace <workplace>
python bin/pf.py search-index doctor --project-root <project> --workplace <workplace>
python bin/pf.py search-index tick --project-root <project> --workplace <workplace>
```

`status` is read-only. `status --verify-files` performs explicit fingerprint
reconciliation and reports stale state when authorized resource content changed.
`refresh` updates indexable resources for the current fresh snapshot. `rebuild`
deletes the derived DB and builds it again. `tick` is the bounded maintenance
unit for operators and Runtime scheduling.

## Runtime And MCP

Runtime maintenance should periodically run `tick` for known projects with
fresh snapshots. PF-owned resource mutations mark existing index state stale;
external file changes are detected by fingerprint verification during `tick`.

`pf.search` never reports stale data as `fresh`. If the index is missing, stale,
or degraded, the result carries that `search_status` and returns no matches
until maintenance refreshes the derived DB.

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
