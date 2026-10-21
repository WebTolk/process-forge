# Test Cases

| ID | Case | Expected | Actual | Status |
|---|---|---|---|---|
| TC-01 | Outbox contains events for current Work | >=1 payload with assignment_id `processforge-pf-outbox-2` | 12 payloads found (sampled) | PASS |
| TC-02 | Hook config enables outbox target | `wtaicc-outbox` enabled, event_types `*` | Confirmed in `.pf/hooks.yaml` | PASS |
| TC-03 | Work transitions emit outbox events | `process.stage.completed` / `transitioned` present | Present in sampled payloads | PASS |
| TC-04 | Kimi Code hooks registered in host config | `[[hooks]]` entries for lifecycle events | Present in `config.toml` | PASS |
| TC-05 | No product code modified | Only audit artifacts under `.pf/artifacts/processforge-pf-outbox-2/` | Confirmed | PASS |
| TC-06 | Previous full audit failure recorded | `full-current-pf-audit-static-executor` status failed | Confirmed in assignment YAML | PASS |
