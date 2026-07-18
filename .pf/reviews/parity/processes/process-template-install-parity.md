# Process Parity: process-template-install

## Result

WARN

## Source

- Path: `processes/process-template-install.yaml`
- Process id: `process-template-install`

## Authoring Coverage

| Area | Status | Notes |
|---|---|---|
| logic_review | WARN | 32 checks |
| unsupported_fields | PASS | 0 unsupported fields |
| semantic_diff | WARN | 1 differences |

## Semantic Diff

- WARN `logic_review`: source definition already has logic review findings: stage intake produces known artifact process-template-request; stage process-definition-creation produces known artifact review; stage process-definition-creation produces known artifact validation-report

## Unsupported Fields

- None.

## Checked

- Process id, run model, roles, stages, artifacts, gates, emitted events, and resource requirements.
- Candidate process logic against ProcessForge authoring rules.

## Skipped

- Byte-for-byte YAML formatting and key order are intentionally not compared.

## Expected WARN

- `logic_review`: source definition already has logic review findings: stage intake produces known artifact process-template-request; stage process-definition-creation produces known artifact review; stage process-definition-creation produces known artifact validation-report

## WARN To Fix Before Public Release

- `logic_review`: source definition already has logic review findings: stage intake produces known artifact process-template-request; stage process-definition-creation produces known artifact review; stage process-definition-creation produces known artifact validation-report

## Recommendation

Process is reproducible with documented warnings; fix action WARN items before public release.
