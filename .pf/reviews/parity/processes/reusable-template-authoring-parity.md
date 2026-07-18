# Process Parity: reusable-template-authoring

## Result

WARN

## Source

- Path: `processes/reusable-template-authoring.yaml`
- Process id: `reusable-template-authoring`

## Authoring Coverage

| Area | Status | Notes |
|---|---|---|
| logic_review | FAIL | 48 checks |
| unsupported_fields | PASS | 0 unsupported fields |
| semantic_diff | WARN | 1 differences |

## Semantic Diff

- WARN `logic_review`: source definition already has logic review findings: stage create-template-structure produces known artifact template-structure; stage register-template produces known artifact template-registry-entry; stage run-template-doctor produces known artifact template-doctor-report; stage select-template-root produces known artifact template-root-selection; stage write-example-files produces known artifact template-examples

## Unsupported Fields

- None.

## Recommendation

Process is reproducible with documented notes; review unsupported fields before public release.
