# Process Parity: bug-fix

## Result

WARN

## Source

- Path: `processes/bug-fix.yaml`
- Process id: `bug-fix`

## Authoring Coverage

| Area | Status | Notes |
|---|---|---|
| logic_review | WARN | 40 checks |
| unsupported_fields | PASS | 0 unsupported fields |
| semantic_diff | WARN | 1 differences |

## Semantic Diff

- WARN `logic_review`: source definition already has logic review findings: stage fix produces known artifact changed-files; stage verify produces known artifact review-findings

## Unsupported Fields

- None.

## Checked

- Process id, run model, roles, stages, artifacts, gates, emitted events, and resource requirements.
- Candidate process logic against ProcessForge authoring rules.

## Skipped

- Byte-for-byte YAML formatting and key order are intentionally not compared.

## Expected WARN

- `logic_review`: source definition already has logic review findings: stage fix produces known artifact changed-files; stage verify produces known artifact review-findings

## WARN To Fix Before Public Release

- `logic_review`: source definition already has logic review findings: stage fix produces known artifact changed-files; stage verify produces known artifact review-findings

## Recommendation

Process is reproducible with documented warnings; fix action WARN items before public release.
