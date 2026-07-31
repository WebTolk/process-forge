# Каскадное объединение

ProcessForge строит execution context, объединяя источники от наименее
специфичных к наиболее специфичным.

Markdown-файлы инструкций, например `AGENTS.md`, не являются машинными
источниками параметров. Если station или global profile должен передавать
машинно-читаемые параметры, он должен явно предоставить структурированный YAML
или JSON источник. В обычном local/workplace режиме вычисление значений
параметров начинается с `workplace`.

## Порядок

```text
core defaults
< workplace
< organization
< direction
< specialization
< platform
< toolchain
< project
< process
< stage
< task
< agent profile
```

## Правила

- Packages загружаются по dependency graph до применения specificity.
- Scalar values заменяются более специфичными values.
- Maps объединяются рекурсивно.
- Lists объединяются по `id`, если элементы list имеют ids.
- Lists без item ids заменяются более специфичным list целиком.
- `null` удаляет map value из более общего слоя.
- Locked policies нельзя переопределять без явного разрешения.
- Blocking conflicts останавливают сборку execution context.
- Итоговый context записывает каждый source и версию package/template.
- Task-level overrides должны быть явными и зафиксированными в log.

## Parameters

`parameters` - нейтральное дерево. ProcessForge не приписывает предметный смысл
ключам вроде `test_stands`, `brand_channels`, `tax_profiles` или
`render_presets`; он только объединяет objects по cascade rules и записывает
provenance.

Parameter values могут объявляться в структурированных источниках workplace,
specialization, platform, project, process, stage, task или agent-profile, если
эти источники активны. Organization и direction являются опциональными слоями:
их можно добавить позже без изменения правил merge.

Inline local credentials являются обычными parameter values для resolver.
Portable/public exports должны предпочитать `auth_ref` или `secret_ref` и
очищать inline secrets согласно export policy.

Текущие file-first источники:

- workplace manifest `parameters`;
- workplace `registries/parameters.yaml`;
- active platform contract `parameters`;
- active specialization `parameters`;
- project manifest `parameters`;
- project local overrides `overrides.parameters`;
- project `.pf/parameters.yaml`;
- project `.pf/parameters.local.yaml`;
- process definition, stage и assignment `parameters`, когда они активны.

Пример:

```yaml
# <workplace-root>/registries/parameters.yaml
schema_version: 1
kind: processforge.parameters
scope: workplace
parameters:
  test_stands:
    - id: local-joomla
      url: http://joomla.local/administrator/
      user: codex
      auth_ref: local.joomla.admin
```

```yaml
# <project-root>/.pf/process-forge.local.yaml
overrides:
  parameters:
    test_stands:
      - id: local-joomla
        user: project-user
        auth_ref: project.local.joomla.admin
```

Итоговый `resolved_parameters.test_stands` сохранит один item `local-joomla` и
добавит project auth reference в workplace object по `id`. Более специфичный
list item может указать `_delete: true` или `__delete__: true`, чтобы удалить
унаследованный item.

## Классы конфликтов

- `informational`: только запись в отчёт.
- `warning`: продолжить работу с review note.
- `blocking`: остановить сборку context до разрешения конфликта.

См. также [вычисление контекста](context-resolution.md) и
[snapshot проектного контекста](project-context-snapshot.md).
