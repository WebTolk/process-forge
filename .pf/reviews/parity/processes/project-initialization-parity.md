# Process Parity: project-initialization

## Result

WARN

## Source

- Path: `processes/project-initialization.yaml`
- Process id: `project-initialization`

## Authoring Coverage

| Area | Status | Notes |
|---|---|---|
| logic_review | WARN | 73 checks |
| unsupported_fields | PASS | 0 unsupported fields |
| semantic_diff | WARN | 1 differences |

## Semantic Diff

- WARN `logic_review`: source definition already has logic review findings: stage apply produces known artifact project-files; stage doctor produces known artifact project-doctor-report; stage global-resource-matching produces known artifact template-matching-report; stage project-classification produces known artifact project-profile; stage project-specificity-extraction produces known artifact project-package-draft; stage workplace-resolution produces known artifact mcp-capability-report; stage workplace-resolution produces known artifact toolchain-detection-report

## Unsupported Fields

- None.

## Checked

- Process id, run model, roles, stages, artifacts, gates, emitted events, and resource requirements.
- Candidate process logic against ProcessForge authoring rules.

## Skipped

- Byte-for-byte YAML formatting and key order are intentionally not compared.

## Expected WARN

- `logic_review`: source definition already has logic review findings: stage apply produces known artifact project-files; stage doctor produces known artifact project-doctor-report; stage global-resource-matching produces known artifact template-matching-report; stage project-classification produces known artifact project-profile; stage project-specificity-extraction produces known artifact project-package-draft; stage workplace-resolution produces known artifact mcp-capability-report; stage workplace-resolution produces known artifact toolchain-detection-report

## Public Release WARN Actions

- None.

## Recommendation

Process is reproducible with documented warnings; public-release action items are listed explicitly when present.
