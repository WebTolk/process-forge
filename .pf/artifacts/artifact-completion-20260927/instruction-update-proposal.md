# Artifact: instruction-update-proposal

## Metadata

- type: instruction-update-proposal
- title: Project instruction improvement proposal
- process: software-feature-development@1.1.0
- status: ready_for_review
- owner_role: orchestrator
- source_assignment: complete-all-required-pf-artifacts-for-the-current-processforge-t01-t10
- content_reference: .pf/artifacts/artifact-completion-20260927/instruction-update-proposal.md
- checksum: sha256:e98fd1df7906187f5bc0b8d5d4edf85ae61cee2fc34aeaf59b8bc4b93b9479bd
- checksum_scope: content_section_utf8_lf
- protection_policy: preserve_after_stage_evidence

## Summary

Project instruction improvement proposal.

## Content

status: proposed; not applied.

target: project-local artifact authoring guidance, narrow project scope.

Proposal: future artifact work should validate text encoding and template placeholders before submitting a transition, and include an artifact-ID index plus explicit applicability for optional outputs. For native Windows shell pipelines, set UTF-8 explicitly or write files through UTF-8-capable file APIs.

Reason/evidence: the first three orchestration records in this Work suffered ASCII conversion; normal PF gates checked evidence presence/hash but could not infer prose readability. The readable r02 revisions and validator demonstrate a corrective practice. Separately, all required historical evidence existed even though the root index was unhelpful.

No process enforcement change or global instruction promotion is requested by this artifact completion. Review any future enforcement separately against language neutrality, valid unknown markers and legitimate historical evidence.

## Review

- status: pass
- reviewer: primary agent; self-review, no independent-review claim
- reviewed_at: 2026-09-27T08:19:03.809993+00:00
