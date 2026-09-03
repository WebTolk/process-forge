# Project Context Service Design

Generated: 2026-08-24 14:45 +04

## Service

`ProjectContextService`

## Responsibilities

- resolve and validate a ProcessForge project root;
- read current snapshot;
- run context freshness checks;
- return compact Garage context payload;
- classify work guidance without requiring a run;
- include session-aware fields only when a valid session is supplied.

## Output Shape

```yaml
kind: pf.context
project:
  id: process-forge
mode: garage
context:
  status: fresh
process:
  id: multi-agent-task-orchestration
resources:
  search_status: ready | empty | stale | blocked
work:
  governed: true | false
  recommendation: start_work | continue
diagnostics: []
```

## Non-Goals

- no raw ingress;
- no private chat;
- no mandatory Ledger lookup;
- no long-lived Runtime dependency.
