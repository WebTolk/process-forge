# Multi-Agent File Flow

ProcessForge supports multi-agent work through files.

## Rule

```text
One file scope = one responsible writer.
```

## Coordination

An orchestrator must:

- create assignments with clear allowed and forbidden files
- avoid parallel writers on the same file scope
- use reviewer-only tasks for overlapping areas
- require handoffs when ownership changes
- record changes in logs and artifacts

## Suitable Subtasks

Subtasks are safest when they are read-only research, review, consistency checks, schema checks, documentation checks, or impact analysis.
