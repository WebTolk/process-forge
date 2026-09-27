# Artifact: domain-model

## Metadata

- type: domain-model
- title: Artifact completeness model
- process: software-feature-development@1.1.0
- status: ready_for_review
- owner_role: orchestrator
- source_assignment: complete-all-required-pf-artifacts-for-the-current-processforge-t01-t10
- content_reference: .pf/artifacts/artifact-completion-20260927/domain-model.md
- checksum: sha256:29900a99571b5035301022baeb3fc02395a3f33a9bc8e6faba03d4c1691f6bb9
- checksum_scope: content_section_utf8_lf
- protection_policy: preserve_after_stage_evidence

## Summary

Artifact completeness model.

## Content

Entities: ProcessDefinition -> Stage -> produced ArtifactId; Assignment -> StageHistory -> Evidence(path, sha256, status); ProjectReport -> sources and observation time; Revision -> predecessor plus correction reason; CoverageIndex -> joins artifact IDs to actual evidence.

Relations are many-to-many: one work has many stages, and one report may serve multiple IDs. Coverage must be keyed by work and artifact ID, not filename alone. A revision does not change a predecessor's recorded hash or assert that the predecessor had the corrected contents.

Invariants: every required current-delivery ID has existing attributable evidence; all claimed evidence hashes match; current Work records are complete; optional outputs have an applicability decision; unknown operational state stays unknown; self-review is not human approval.

## Review

- status: pass
- reviewer: primary agent; self-review, no independent-review claim
- reviewed_at: 2026-09-27T08:06:31.590984+00:00
