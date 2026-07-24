# Process Parity: software-feature-development

## Result

WARN

## Source

- Path: `processes/software-feature-development.yaml`
- Process id: `software-feature-development`

## Authoring Coverage

| Area | Status | Notes |
|---|---|---|
| logic_review | WARN | 49 checks |
| unsupported_fields | PASS | 0 unsupported fields |
| semantic_diff | WARN | 1 differences |

## Semantic Diff

- WARN `logic_review`: source definition already has logic review findings: stage architecture produces known artifact decision-log; stage assurance produces known artifact review-findings; stage implementation produces known artifact changed-files

## Unsupported Fields

- None.

## Checked

- Process id, run model, roles, stages, artifacts, gates, emitted events, and resource requirements.
- Candidate process logic against ProcessForge authoring rules.

## Skipped

- Byte-for-byte YAML formatting and key order are intentionally not compared.

## Expected WARN

- `logic_review`: source definition already has logic review findings: stage architecture produces known artifact decision-log; stage assurance produces known artifact review-findings; stage implementation produces known artifact changed-files

## Public Release WARN Actions

- None.

## Recommendation

Process is reproducible with documented warnings; public-release action items are listed explicitly when present.
