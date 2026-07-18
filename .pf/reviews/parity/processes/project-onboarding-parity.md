# Process Parity: project-onboarding

## Result

WARN

## Source

- Path: `processes/project-onboarding.yaml`
- Process id: `project-onboarding`

## Authoring Coverage

| Area | Status | Notes |
|---|---|---|
| logic_review | WARN | 58 checks |
| unsupported_fields | PASS | 0 unsupported fields |
| semantic_diff | WARN | 1 differences |

## Semantic Diff

- WARN `logic_review`: source definition already has logic review findings: stage detect-project produces known artifact global-resource-matching-report; stage detect-project produces known artifact project-classification-report; stage validate produces known artifact project-doctor-report

## Unsupported Fields

- None.

## Checked

- Process id, run model, roles, stages, artifacts, gates, emitted events, and resource requirements.
- Candidate process logic against ProcessForge authoring rules.

## Skipped

- Byte-for-byte YAML formatting and key order are intentionally not compared.

## Expected WARN

- `logic_review`: source definition already has logic review findings: stage detect-project produces known artifact global-resource-matching-report; stage detect-project produces known artifact project-classification-report; stage validate produces known artifact project-doctor-report

## WARN To Fix Before Public Release

- `logic_review`: source definition already has logic review findings: stage detect-project produces known artifact global-resource-matching-report; stage detect-project produces known artifact project-classification-report; stage validate produces known artifact project-doctor-report

## Recommendation

Process is reproducible with documented warnings; fix action WARN items before public release.
