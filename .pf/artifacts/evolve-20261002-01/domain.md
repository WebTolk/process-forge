# Domain Modeling: evolve-20261002-01

Domain terms:
- Scope intent: explicit local operator JSON passed through `work-start --scope-file`.
- Normalized execution mode: the effective mode stored in assignment intent, including `code_changes_allowed` and `artifact_changes_allowed`.
- Effective permission readiness: derived action/path capability computed by `permission_readiness`.
- Durable Work publication: writing the capsule, Run, Assignment, task index and lifecycle events.

Rules:
1. Scope syntax validation, source/output readiness, overlap checks and effective permission readiness are all pre-publication checks for explicit scope creation.
2. An implementation-mode assignment without `write_product` is not executable for product changes and must not be published as newly created Work.
3. A planning/read-only analysis-style assignment may be ready with read and artifact-write grants while still lacking `write_product`.
4. A retry after a slow or timed-out start must preserve exact objective/intent identity; changed scope requires a successor objective rather than blind widening.
5. Existing capsules, predecessor assignments and unrelated active writers remain immutable and authoritative.

Model boundary:
- This task changes only explicit scope creation. It does not reclassify every legacy/unscoped Work start, and it does not change CLI parser ownership.
