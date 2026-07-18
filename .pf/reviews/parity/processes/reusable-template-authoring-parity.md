# Process Parity: reusable-template-authoring

## Result

WARN

## Source

- Path: `processes/reusable-template-authoring.yaml`
- Process id: `reusable-template-authoring`

## Authoring Coverage

| Area | Status | Notes |
|---|---|---|
| logic_review | WARN | 48 checks |
| unsupported_fields | PASS | 0 unsupported fields |
| semantic_diff | WARN | 1 differences |

## Semantic Diff

- WARN `logic_review`: source definition already has logic review findings: stage create-template-structure produces known artifact template-structure; stage register-template produces known artifact template-registry-entry; stage run-template-doctor produces known artifact template-doctor-report; stage select-template-root produces known artifact template-root-selection; stage write-example-files produces known artifact template-examples

## Unsupported Fields

- None.

## Checked

- Process id, run model, roles, stages, artifacts, gates, emitted events, and resource requirements.
- Candidate process logic against ProcessForge authoring rules.

## Skipped

- Byte-for-byte YAML formatting and key order are intentionally not compared.

## Expected WARN

- `logic_review`: source definition already has logic review findings: stage create-template-structure produces known artifact template-structure; stage register-template produces known artifact template-registry-entry; stage run-template-doctor produces known artifact template-doctor-report; stage select-template-root produces known artifact template-root-selection; stage write-example-files produces known artifact template-examples

## WARN To Fix Before Public Release

- `logic_review`: source definition already has logic review findings: stage create-template-structure produces known artifact template-structure; stage register-template produces known artifact template-registry-entry; stage run-template-doctor produces known artifact template-doctor-report; stage select-template-root produces known artifact template-root-selection; stage write-example-files produces known artifact template-examples

## Recommendation

Process is reproducible with documented warnings; fix action WARN items before public release.
