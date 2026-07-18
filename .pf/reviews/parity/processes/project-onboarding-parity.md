# Process Parity: project-onboarding

## Result

WARN

## Source

- Path: `processes/project-onboarding.yaml`
- Process id: `project-onboarding`

## Authoring Coverage

| Area | Status | Notes |
|---|---|---|
| logic_review | FAIL | 58 checks |
| unsupported_fields | PASS | 0 unsupported fields |
| semantic_diff | WARN | 1 differences |

## Semantic Diff

- WARN `logic_review`: source definition already has logic review findings: stage detect-project produces known artifact global-resource-matching-report; stage detect-project produces known artifact project-classification-report; stage validate produces known artifact project-doctor-report

## Unsupported Fields

- None.

## Recommendation

Process is reproducible with documented notes; review unsupported fields before public release.
