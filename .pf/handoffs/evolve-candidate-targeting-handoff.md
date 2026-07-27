# Evolve Candidate Targeting Handoff

- timestamp: `2026-07-27T23:07:45+04:00`
- agent: Codex
- status: ready for release gates

## Changed Areas

- `tools/processforge.py`
- `schemas/knowledge-candidate.schema.json`
- `schemas/process-definition.schema.json`
- `schemas/process-authoring-answers.schema.json`
- `templates/knowledge-candidate.yaml`
- `templates/process-authoring-answers.yaml`
- `templates/process.yaml`
- `templates/process-definition-template.yaml`
- `processes/*.yaml`
- `docs/concepts/*evolve*`, `docs/concepts/knowledge-*`, `docs/concepts/platform-inheritance.md`
- `docs/ru/...` evolve/authoring/concepts pages
- `examples/evolve-targeting/*`
- `tools/smoke_*evolve*targeting*.py`
- `tools/smoke_knowledge_hub_routes_by_target.py`
- `tools/smoke_child_platform_not_promoted_to_parent.py`

## Next Steps

1. Refresh `checksums/processforge.sha256`.
2. Run public release-test fail-fast and full.
3. Run `release-pack` and full `release-archive-test`.
4. Commit and push.
