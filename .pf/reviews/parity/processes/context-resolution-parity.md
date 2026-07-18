# Process Parity: context-resolution

## Result

WARN

## Source

- Path: `processes/context-resolution.yaml`
- Process id: `context-resolution`

## Authoring Coverage

| Area | Status | Notes |
|---|---|---|
| logic_review | WARN | 59 checks |
| unsupported_fields | PASS | 0 unsupported fields |
| semantic_diff | WARN | 1 differences |

## Semantic Diff

- WARN `logic_review`: source definition already has logic review findings: stage ecp-capsule-generation produces known artifact execution-context-package; stage rule-classification produces known artifact classified-rules; stage source-discovery produces known artifact source-inventory

## Unsupported Fields

- None.

## Checked

- Process id, run model, roles, stages, artifacts, gates, emitted events, and resource requirements.
- Candidate process logic against ProcessForge authoring rules.

## Skipped

- Byte-for-byte YAML formatting and key order are intentionally not compared.

## Expected WARN

- `logic_review`: source definition already has logic review findings: stage ecp-capsule-generation produces known artifact execution-context-package; stage rule-classification produces known artifact classified-rules; stage source-discovery produces known artifact source-inventory

## WARN To Fix Before Public Release

- `logic_review`: source definition already has logic review findings: stage ecp-capsule-generation produces known artifact execution-context-package; stage rule-classification produces known artifact classified-rules; stage source-discovery produces known artifact source-inventory

## Recommendation

Process is reproducible with documented warnings; fix action WARN items before public release.
