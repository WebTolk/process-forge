# Process Parity: process-supervisor

## Result

WARN

## Source

- Path: `processes/process-supervisor.yaml`
- Process id: `process-supervisor`

## Authoring Coverage

| Area | Status | Notes |
|---|---|---|
| logic_review | WARN | 39 checks |
| unsupported_fields | PASS | 0 unsupported fields |
| semantic_diff | WARN | 1 differences |

## Semantic Diff

- WARN `logic_review`: source definition already has logic review findings: stage start produces known artifact exit-record; stage start produces known artifact process-record; stage start produces known artifact worker-logs

## Unsupported Fields

- None.

## Checked

- Process id, run model, roles, stages, artifacts, gates, emitted events, and resource requirements.
- Candidate process logic against ProcessForge authoring rules.

## Skipped

- Byte-for-byte YAML formatting and key order are intentionally not compared.

## Expected WARN

- `logic_review`: source definition already has logic review findings: stage start produces known artifact exit-record; stage start produces known artifact process-record; stage start produces known artifact worker-logs

## WARN To Fix Before Public Release

- `logic_review`: source definition already has logic review findings: stage start produces known artifact exit-record; stage start produces known artifact process-record; stage start produces known artifact worker-logs

## Recommendation

Process is reproducible with documented warnings; fix action WARN items before public release.
