# Software Feature Development Process Authoring Example

This example points to the stable `software-feature-development` process from
the official bundled `processforge.official.software-development` pack.

- Process: `packs/official/software-development/processes/software-feature-development.yaml`
- Prompt: `packs/official/software-development/prompts/software-feature-development-agent.md`
- Documentation: `packs/official/software-development/docs/processes/software-feature-development.md`

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

Activate the official pack in the project's linked workplace, then validate:

```bash
python bin/pf.py pack-activate --id processforge.official.software-development --workplace <workplace-root> --apply
python bin/pf.py process-doctor --project-root . --process software-feature-development --contract-only
```
