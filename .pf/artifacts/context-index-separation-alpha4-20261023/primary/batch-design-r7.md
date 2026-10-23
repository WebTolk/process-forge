# Batch knowledge addition and targeted final indexing

User steering explicitly authorizes this cohesive alpha4 extension and supersedes
the old refactor-only default for these exact new commands. The existing r10 tree,
QA, rejected review and canceled unused review reservation stay immutable.

## Domain and acceptance

Add `knowledge-add-batch --workplace ROOT --package ID --batch-file FILE`
with optional `--package-root`, `--apply`, `--dry-run`, `--json`. The YAML envelope
is `schema_version: 1` and `resources: [...]`: inline records use exactly the
existing knowledge-add-resource record format, including URL source records.
No downloading, package creation, project selection or external service changes.
Empty/malformed envelopes and duplicate explicit resource IDs fail before writes.
Default and --dry-run are read-only, --apply plus --dry-run is refused.

Reuse build_knowledge_resource_add_plan, preflight_authoring_plan and
execute_authoring_plan through injected callbacks. Prepare each applied item
against the latest manifest immediately before its commit: never publish several
plans made from the same old manifest. Preserve manifest/index/private-registry
transaction guarantees and native post-commit audit/recovery. Continue ordinary
item validation/commit errors; report each result in input order with portable
error codes. Do not swallow KeyboardInterrupt/SystemExit cancellation except the
known legacy validation SystemExit boundary. A post-commit audit error is a failed
item, never an unqualified successful addition; existing recovery evidence remains.

Collect unique successfully completed resource IDs. After all items, call the
canonical maintenance owner's new run_resources method exactly once with only
those IDs. No successful IDs means no indexing call. A final indexing error does
not roll back committed additions: retain successful rows and report a separate
indexing failure and nonzero CLI exit. Mixed failures also exit nonzero. No
per-item build, full workplace reconciliation or retry loop is allowed.

## Architecture and ownership

The same logical native maintenance contributor receives a new bounded Work for
new knowledge_batch Core service, thin CLI/parser and behavioral tests only.
The primary integrates Main through a clean-HEAD projection under its aggregate
Work and implements run_resources under its current review-correction Work.
Existing native integration scope covers EN/RU concept documentation; aggregate
scope covers release notes. No concurrent writer touches the same file.

Targeted indexing resolves IDs against the live registered catalogue, then passes
a strictly narrowed non-workplace snapshot to the existing backend.refresh under
the canonical bounded writer lock and durable running/terminal receipts. It must
retain all unselected SQLite rows and never scan unselected document bodies.
Unknown/missing IDs fail closed; an empty selection is not global authorization.
Use the actual existing backend Protocol; no extra database backend or DAL.

A targeted receipt proves only that selected resources were indexed. It must not
acknowledge an older workplace invalidation, preceding failure or an invalidation
arriving during its run, nor declare all resources globally fresh. Report selected
index success separately from the observation's global readiness. Full workplace
verification/reconciliation remains explicit manual maintenance or the cold future
scheduler callable; no periodic scheduler is implemented in this release.

Tests: dry-run/no effects, envelope/duplicates, no lost manifest updates, mixed
success/failure/order, all-failed/no indexing, one final selected call, index error
after commits, post-commit audit error, selected SQLite replacement with unrelated
body-read refusal and unchanged unrelated rows, pending/global failure preservation,
unknown IDs and busy writer. Repeat registered QA and independent native final review
on a new candidate; no commit/push/publication until CODE GO.
