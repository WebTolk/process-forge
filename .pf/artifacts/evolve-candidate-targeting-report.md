# Evolve Candidate Targeting Report

- timestamp: `2026-07-27T23:07:45+04:00`
- agent: Codex
- task: `задания/processforge_evolve_candidate_targeting_applicability_master_prompt.md`
- status: implemented

## Scope

Implemented explicit candidate targeting for the common `evolve` mechanism:

- `source_context`
- object `target`
- `applicability`
- `generalization`
- `routing`
- `applicability_confidence`
- `promotion`

## Implementation

- Extended knowledge candidate schema and YAML template.
- Updated ProcessForge CLI validation, queue index, export, hub import, and package build routing.
- Made `knowledge-package-build-from-candidates` select only matching `routing.recommended_destination.id` or `target.id`.
- Staged unapproved parent-platform candidates in `resources/incoming-learnings.md` instead of curated package notes.
- Added process-authoring `candidate_targeting` questions and materialized process requirements.
- Added built-in process evolve hints for software feature development, content production, and testing.
- Added synthetic examples under `examples/evolve-targeting/`.
- Added targeted smokes for schema, narrowest scope, split guidance, hub routing, child-parent promotion, authoring, and sanitizer coverage.

## Verification

Targeted new smokes passed:

- `python tools/smoke_evolve_candidate_targeting_schema.py`
- `python tools/smoke_evolve_candidate_narrowest_scope.py`
- `python tools/smoke_evolve_candidate_split_guidance.py`
- `python tools/smoke_knowledge_hub_routes_by_target.py`
- `python tools/smoke_child_platform_not_promoted_to_parent.py`
- `python tools/smoke_process_authoring_evolve_targeting.py`
- `python tools/smoke_evolve_targeting_privacy_sanitizer.py`

Existing evolve smokes passed:

- `python tools/smoke_evolve_candidate_schema.py`
- `python tools/smoke_workplace_learning_queue.py`
- `python tools/smoke_evolve_candidate_export.py`
- `python tools/smoke_evolve_privacy_sanitizer.py`
- `python tools/smoke_knowledge_hub_import.py`
- `python tools/smoke_knowledge_package_build_from_candidates.py`
- `python tools/smoke_knowledge_package_release_update_manifest.py`
- `python tools/smoke_evolve_learning_loop_end_to_end.py`
- `python tools/smoke_process_authoring_evolve_questions.py`
- `python tools/smoke_process_authoring_materializes_evolve.py`

Broader checks passed before release packaging:

- `python -m py_compile ...`
- `python tools/validate-process-forge-schemas.py --root .`
- `python tools/validate-public-cleanliness.py --root .`

## Follow-Up

Run full public release gates, refresh checksums and distribution archive, then commit and push the combined evolve slice.
