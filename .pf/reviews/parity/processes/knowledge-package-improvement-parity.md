# Process Parity: knowledge-package-improvement

## Result

WARN

## Source

- Path: `processes/knowledge-package-improvement.yaml`
- Process id: `knowledge-package-improvement`

## Authoring Coverage

| Area | Status | Notes |
|---|---|---|
| logic_review | WARN | 37 checks |
| unsupported_fields | PASS | 0 unsupported fields |
| semantic_diff | WARN | 1 differences |

## Semantic Diff

- WARN `logic_review`: source definition already has logic review findings: stage integrate produces known artifact change-summary

## Unsupported Fields

- None.

## Checked

- Process id, run model, roles, stages, artifacts, gates, emitted events, and resource requirements.
- Candidate process logic against ProcessForge authoring rules.

## Skipped

- Byte-for-byte YAML formatting and key order are intentionally not compared.

## Expected WARN

- `logic_review`: source definition already has logic review findings: stage integrate produces known artifact change-summary

## Public Release WARN Actions

- None.

## Recommendation

Process is reproducible with documented warnings; public-release action items are listed explicitly when present.
