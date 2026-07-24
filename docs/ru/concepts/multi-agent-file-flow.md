# Multi-Agent File Flow

ProcessForge поддерживает multi-agent работу через файлы.

Для готового процесса и CLI-команд см.
[Multi-agent orchestration](multi-agent-orchestration.md).

## Правило

```text
One file scope = one responsible writer.
```

## Coordination

Orchestrator должен:

- создавать assignments с ясными allowed и forbidden files
- избегать parallel writers на одном file scope
- использовать reviewer-only tasks для пересекающихся областей
- требовать handoffs при смене ownership
- записывать изменения в logs и artifacts
- создавать worker launch prompts, где есть только assigned task и capsule

## Suitable Subtasks

Самые безопасные subtasks: read-only research, review, consistency checks,
schema checks, documentation checks и impact analysis.
