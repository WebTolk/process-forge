# Index storage decision: local default and replaceable search backends

Status: architecture decision for the alpha4 successor; no backend has been added
or switched. Incorporates the operator's request to consider SQLite, adapter-based
databases and RAG without silently expanding this task into the separate DB program.
Read first: architecture-r2.md. Earlier architecture/capsules remain immutable.

## Decision

Keep the existing SQLite FTS5 backend as the alpha4 default and reuse its engine.
The current private derived index belongs to the workplace, at the portable
location <workplace>/runtime/search/local-resource-search.sqlite. It does not
belong to a project checkout, the installed Core directory, release assets or the
public knowledge package. Projects and Work carry authorization references, not
copies of workplace search documents. Index data may contain private text and
must retain the workplace's access/privacy boundary.

Separate three responsibilities:

1. Indexing application component: explicit request/scope validation, selecting
   registered sources, operation ownership, progress, serialization, retry and
   recovery. CLI and the future scheduler call this same component; all mutating
   CLI indexing operations must converge here while retaining released flags,
   scoped behavior, output/error mapping and exit codes. No adapter owns a second
   indexing algorithm. Project refresh/read/query never starts this component.
2. Search/index backend: the concrete fulltext/vector/hybrid operations and index
   lifecycle. The existing ResourceSearchIndex is the SQLite implementation to
   reuse. A narrow operation Protocol/factory belongs at this real boundary; do
   not add a nominal wrapper or universal database god object just to count classes.
3. Connection/storage infrastructure: future shared DB API and PFConfig named
   connection profiles own SQL connections, transactions, TLS, timeouts and secret
   references. Search consumes that infrastructure through its backend. Reuse the
   already registered pf-database-layer-and-journals-20261021 program rather than
   implementing a second DAL, SQL builder, ORM or pool under resources.

## Backend capabilities

SQLite FTS5 supplies today's lexical/fulltext search. MySQL/MariaDB/PostgreSQL
could back a later adapter only after real integration/conformance tests; a SQL
connection alone does not supply identical tokenization, ranking, fulltext syntax,
constraints or transaction guarantees. A backend advertises tested capabilities,
not a fiction that every database supports the same operations.

Vector and hybrid retrieval are separate capabilities. RAG is the application
pipeline retrieve -> augment model input -> generate, not a database driver.
It can use lexical, semantic, vector or hybrid retrieval. If later selected, a
vector index additionally needs explicit chunking/embedding model/version/dimension
and generation identity, update/delete propagation, access filtering and costs.
Choosing a particular vector product or invoking external embeddings is outside
alpha4. Do not claim MySQL/vector/RAG support from the SQLite-only implementation.

## Invariants shared by adapters

* Resource/document IDs, provenance, source hashes and generation identity remain
  stable; private absolute roots are resolved privately, never public locators.
* Query filters apply authorized project/Work/resource identities before results,
  counts, ranking/snippets or retrieved context can disclose other resources.
  A physical shared store or new driver never grants additional access.
* Required source/access freshness remains live. Missing, stale, running, failed
  or incomplete maintenance stays distinguishable from a ready context; no hidden
  indexing, network connection, embedding generation or migration from config read.
* Maintenance serialization/recovery belongs to the common component; a failed
  refresh cannot present incomplete data as a complete current index generation.
  Readers and writers use the existing engine's tested transaction guarantees.
* Search indexes are derived and reconstructible from authorized source material;
  operational journals/accounting are durable facts with a different retention
  contract. Keep index rebuild/cleanup separate from journal migration and audit.
* Default local use requires no external service. Remote backend selection and
  credential references require explicit configuration and a governed migration
  or rebuild, with old state retained until the new backend is qualified.

## Scope of alpha4

Implement context/index responsibility separation and the single component on the
existing SQLite engine, plus the small genuine backend seam needed by actual
consumers. Preserve the existing physical location and file-only mode. Document
the future scheduler callback and storage extension boundary. Multi-backend DAL,
actual MySQL/PostgreSQL/vector adapters and RAG remain separate governed tasks.
The release must say SQLite-only until another backend is really tested.

## Sources consulted

Local: existing local_search.py, resources/access.py, resource-search-index.md,
pf-database-layer-backlog-20261021/spec.md and its journal-storage-requirements.md
and python-data-layer-comparison.md. Existing storage and authorization were read
from current source, not inferred from a product name.

Primary verification, 2026-10-23: [SQLite FTS5](https://www.sqlite.org/fts5.html)
describes its fulltext virtual tables and ranking;
[Microsoft RAG/index overview](https://learn.microsoft.com/azure/ai-studio/concepts/retrieval-augmented-generation)
distinguishes the retrieval/augmentation/generation pipeline and retrieval modes.
The PF layering/backend recommendation above is our design inference, not a claim
that either source describes this repository or that Azure is selected.
