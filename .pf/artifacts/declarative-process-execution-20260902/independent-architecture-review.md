# Independent Architecture Review

Reviewer: Codex architecture reviewer and PF shell-agent reviewer.
Date: 2026-09-02

Initial verdict: FAIL.

The review identified bypassable evidence, incomplete `stage_completion`, stale live-YAML projection data, hidden caller stage selection, incomplete event schema and missing shared locking with legacy lifecycle commands.

## Resolution

- artifacts and gates now require typed evidence; attestation cannot satisfy them;
- `not_applicable` evidence requires reason and supporting evidence;
- `handoff_note_required`, entry gates, `required_artifacts`, `required_evidence`, optional artifacts consumed by later inputs and sibling blocking assignments are evaluated;
- public `preferred_stage` is rejected;
- runtime stage contract comes from the pinned Process state;
- stage-event payload requirements and persisted execution fields are schema-defined;
- start uses a registry lock and legacy summary/completion commands use the same per-Run lock.

Residual limitation: cross-file Run/Assignment/summary/event persistence is atomic per file and serialized per Run, not an ACID multi-file transaction. The existing doctor and canonical state checks remain the recovery guard.
