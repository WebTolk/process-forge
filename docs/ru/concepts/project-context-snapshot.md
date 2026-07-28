# Project Context Snapshot

Project context snapshot - вычисленная операционная карта проекта ProcessForge.
Она создаётся при project init или project refresh и читается в начале сессии.

Основные пути:

```text
.pf/contexts/project-context.snapshot.yaml
.pf/contexts/project-context.snapshot.md
.pf/contexts/project-context.snapshots/<snapshot-id>.yaml
.pf/runtime/cache/workplace-context.snapshot.yaml
```

Snapshot различает доступные platform contracts и выбранный platform stack.
Для `agent-workspace`, `brownfield-workspace` и `meta-workspace` нормально иметь
доступные contracts без выбранного stack:

```yaml
available_platform_contracts:
  - id: platform.joomla
selected_platform_contracts: []
platform_stack: []
platform_selection:
  status: not_applicable
```

Для обычного проекта, например `joomla-extension`, выбранные platform contracts
попадают в `selected_platform_contracts` и `platform_stack`.

Runtime workplace snapshot может содержать локальную availability-информацию о
tools и MCP. Он лежит в `.pf/runtime/cache/` и остаётся private.
