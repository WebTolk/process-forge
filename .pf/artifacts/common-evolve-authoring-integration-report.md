# Common Evolve Authoring Integration Report

## Summary

Common `evolve` is now a process-agnostic top-level process contract. It is separate from legacy `evolution_policy`: `evolution_policy` remains compatibility/run-upgrade policy, while `evolve` controls reusable learning extraction, local candidates, privacy, and apply boundaries.

## Implemented

- Process definition schema supports top-level `evolve`.
- Process authoring answers schema requires explicit `evolve` decision.
- Process authoring templates, questions, prompt, materializer, import/backfill, and logic review preserve `evolve`.
- Every built-in process YAML declares explicit `evolve`.
- New schemas exist for `processforge.evolution_report` and `processforge.knowledge_candidate`.
- CLI MVP covers `evolve-run`, candidate sanitize/create/list/export, `knowledge-hub-init`, `knowledge-hub-import`, `knowledge-package-build-from-candidates`, and `knowledge-package-release`.
- Workplace learning queue persists under `<workplace>/learning/`.
- Hub release writes a file-provider update manifest for the existing update pipeline.

## Boundaries

- Candidates are local until sanitized export.
- Hub package build writes `candidate-notes.md`; it does not silently rewrite curated docs.
- Package updates are distributed through update candidates/stage/verify/apply.
- Project context snapshots are not refreshed silently after package updates.
- The MVP does not implement full governance, multi-reviewer curation, ranking, conflict resolution, semantic search, remote sync, package signing, UI, or automatic global package application.

## Validation

- `python tools/validate-process-forge-schemas.py --root .` - PASS.
- `python tools/validate-public-cleanliness.py --root .` - PASS.
- `python tools/validate-process-forge-checksums.py --root . --check` - PASS.
- 14 new evolve smokes run directly - PASS.
- Existing targeted catalog/schema/authoring/context/update/lifecycle smokes - PASS.
- `python bin/pf.py release-test --root . --only smoke_process_authoring_materializes_evolve --public --fail-fast --timeout-scale 1` - PASS.
- `python bin/pf.py release-test --root . --only smoke_evolve_learning_loop_end_to_end --public --fail-fast --timeout-scale 1` - PASS.
- `python bin/pf.py release-test --root . --public --fail-fast --timeout-scale 1` - PASS.
- `python bin/pf.py release-test --root . --public --timeout-scale 1` - PASS.
- `python bin/pf.py release-pack --root . --output dist/processforge.zip` - PASS.
- `python bin/pf.py release-archive-test --archive dist/processforge.zip --root . --extracted-test full --timeout-scale 1` - PASS.
