# Governed Work Bootstrap Design

Generated: 2026-08-24 14:00 +04

## Goal

Garage entry should give an agent a safe first action without guessing process
stages or creating out-of-contract tasks.

## Proposed Contract

Expose one high-level bootstrap surface that reads the current project manifest,
process definition, active run/task state, context freshness, session binding,
and search readiness, then returns a bounded next-action payload:

```yaml
kind: pf.governed_work.bootstrap
project_root: <requested project>
session:
  status: bound | missing | invalid
process:
  id: <process id>
  valid_stages:
    - <stage ids from process definition>
work:
  run_status: none | active | blocked | complete
  next_allowed_actions:
    - create_run
    - create_task
    - start_task
    - refresh_context
search_readiness:
  infrastructure: ready | blocked
  corpus: ready | empty | blocked
diagnostics:
  - code: <machine-readable code>
```

## Safety Rules

- Stages must come from the selected process definition only.
- The API must not synthesize fake session ids.
- Missing session returns remediation instead of creating work.
- Search readiness must distinguish fresh-empty from fresh-searchable.
- Runtime and MCP are diagnostics providers, not separate process authority.

Status: `design_ready`, implementation not included in this slice.
