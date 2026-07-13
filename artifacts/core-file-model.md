# Artifact: core-file-model

## Metadata

- type: file-model
- title: ProcessForge Core File Model
- process: knowledge-package-improvement@0.1.0
- status: approved
- owner_role: orchestrator
- source_assignment: pf-bootstrap-orchestrator
- content_reference: artifacts/core-file-model.md
- checksum: pending
- protection_policy: protected_after_bootstrap

## Model

ProcessForge uses these core file groups:

- `process-forge.yaml`: project manifest and policy root.
- `AGENTS.md`: agent boot and work rules.
- `processes/`: versioned process definitions.
- `packages/`: versioned knowledge package manifests.
- `templates/`: reusable templates.
- `assignments/`: bounded work requests.
- `contexts/`: immutable Execution Context Packages.
- `artifacts/`: durable outputs.
- `reviews/`: review results and findings.
- `handoffs/`: transfer notes between roles.
- `logs/`: append-only work and verification records.
- `adr/`: durable architecture decisions.
- `tools/`: file-only validators.

## Traceability

Every work unit should connect:

```text
assignment -> context -> artifacts -> review -> handoff -> logs
```
