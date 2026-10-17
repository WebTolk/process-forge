# Domain notes / model / rules

A metadata read pass is an explicit operation-local acquisition of derived facts, not a new Work identity, lifecycle record or authority source. It captures ordered Run paths and compact current document observations as consumed. Private snapshots are never returned by reference; consumer dictionaries are independent. A new pass after every operation/write rechecks current files, while only safe compact parse results survive in the existing bounded process cache.

Source fields: Run id/status/process/objective/tasks/created_at/updated_at/error; Assignment id/run_id/status/stage/process/objective/session/created_at/updated_at/error. Unusual empty selected projections use full fallback to preserve source truthiness/type behavior. Existing flat field projection is reused; no custom loader/constructor policy is introduced.

Distinct owners remain: WorkProjectionPolicy for summary, WorkRecordCatalogService for candidate facts, WorkSelectionService for choice, CompletionIntentReadService/ValidationService for journal validity and ProcessExecutionService for full current Work validation. Completion presence is checked against raw valid ids even for terminal Run; actual validation result is not retained across requests.

No global TTL, mtime-only trust, write-side invalidation or request-wide ContextVar snapshot. Factory defaults create fresh passes when catalog is requested; an explicit provider allows the pf.context summary and catalog to share exactly one pass. Injected full record readers retain their original behavior unless an explicit metadata provider is supplied. Exact canonical pair requests do not acquire global metadata. Domain rules captured.
