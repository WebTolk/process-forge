# Software Feature Development Process Authoring Example

This example points to the public stable built-in
`software-feature-development` from the optional `software-web` domain pack.

- Process: `examples/domain-packs/software-web/processes/software-feature-development.yaml`
- Prompt: `examples/domain-packs/software-web/prompts/software-feature-development-agent.md`
- Documentation: `examples/domain-packs/software-web/docs/processes/software-feature-development.md`

## Compact Lifecycle

A small feature task can use `lifecycle_mode: feature` or `debug_loop` and still
record the conditional stages explicitly:

```yaml
lifecycle_mode: feature
stage_decisions:
  release-delivery:
    status: not_applicable
    reason: Local development change only; no release requested.
    evidence:
      - .pf/artifacts/scope.md
      - .pf/artifacts/test-report.md
  evolve:
    status: completed
    artifacts:
      - .pf/artifacts/evolve/evolution-report.md
```

## Release-Ready Lifecycle

A release-ready task includes delivery artifacts and runs a project/platform
delivery profile as an operation:

```yaml
process_id: software-feature-development
lifecycle_mode: full
execution_profile:
  delivery_profile: project.default_delivery
expected_artifacts:
  - delivery-plan
  - delivery-report
  - release-notes
  - migration-notes
  - patch
```

Validate with:

```bash
python bin/pf.py process-doctor --project-root . --process software-feature-development --contract-only
```
