# Private Pattern Research

This internal note records reusable learning from the provided `.webtolk` flow. It is excluded from release inventory.

## Reusable Patterns

- Artifact-driven stages with explicit inputs, outputs, gates, and blocking conditions.
- Required artifacts by stage.
- Handoff contracts before stage transition.
- Capability-first tool policy with fallback telemetry.
- Split logs for task progress, agent actions, verification evidence, and tool telemetry.
- Overlay model where platform, toolchain, domain, and project rules extend core rules.
- Evolution loop for reusable learning.
- Template discipline with required sections and explicit "Not applicable" reasons.

## Do Not Transfer Directly

- Local paths and machine-specific tool names.
- Platform-specific or language-specific assumptions in core.
- Migration history.
- Internal artifact paths as universal defaults.

## Public Abstractions To Use

- `StageDefinition`
- `ArtifactType`
- `HandoffContract`
- `ToolCapabilityPolicy`
- `ProjectContextOverlay`
- `EvidenceLog`
- `EvolutionProposal`
- `FlowValidator`

## Risks

- Contract/template drift if validators do not check both.
- Tool policy becomes too local if concrete tools are hardcoded.
- Logging becomes busywork without automation.
- Evolution proposals need approval boundaries.
