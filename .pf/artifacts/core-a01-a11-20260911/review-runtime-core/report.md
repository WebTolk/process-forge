# review-runtime-core-report

## Verdict

Conditional pass. Targeted validation artifacts pass, but two correctness findings remain.

## Findings

### P2 — Multi-root resources silently lose documents

- File/lines: `src/processforge_core/local_resource_search.py:428-435`, schema uniqueness at `:554`
- Scenario: one resource declares multiple `content_roots`, each containing `same.md`.
- Cause: `_documents()` deduplicates only by `(resource_id, relative_path)`, so the second root’s document is discarded.
- Acceptance: include canonical root identity in document identity/storage, or explicitly reject multi-root resources; add a regression test.

### P2 — Symlink loops can escape graceful degradation

- File/lines: `src/processforge_core/local_resource_search.py:314-316`, `:386-400`
- Scenario: an authorized root or descendant contains a symlink loop.
- Cause: `Path.resolve()` may raise `RuntimeError`, but only `OSError` is caught.
- Acceptance: catch symlink-resolution failures and skip/report the affected resource as degraded rather than aborting search/index maintenance.

## Unverified residual risk

- `src/processforge_core/core_update.py:334-337` and `:391-394`: migration preflight checks `copy_if_missing` targets, but apply does not re-check them. A concurrent file creation can be overwritten; registry append operations have the analogous duplicate-entry race. Add apply-time checks or serialize planning/apply if concurrent workplace updates are supported.

## Evidence reviewed

- Current artifacts report PASS for scheduler isolation, singleton orphan handling, search containment/source integrity, migration-source validation, long-lived runtime, and runtime status timeout.
- Static review confirms shared singleton guarding across cleanup/acquire/release, live-orphan refusal, dead-owner recovery, schema-based old-index invalidation, migration source preflight, and durable partial-migration records.
- Serena was unavailable; review used targeted source inspection and existing validation artifacts.