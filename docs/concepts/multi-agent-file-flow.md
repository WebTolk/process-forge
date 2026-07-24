# Multi-Agent File Flow

ProcessForge supports multi-agent work through files.

For the out-of-box process and CLI commands, see
[Multi-agent orchestration](multi-agent-orchestration.md).

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
- create worker launch prompts that include only the assigned task and capsule

## Suitable Subtasks

Subtasks are safest when they are read-only research, review, consistency checks, schema checks, documentation checks, or impact analysis.
