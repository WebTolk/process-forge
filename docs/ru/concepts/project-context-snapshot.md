# Project Context Snapshot

Project context snapshot - вычисленная operational map проекта ProcessForge. Он
создается во время project init или project-context-refresh и читается в начале
сессии до широких scans по packages или templates.

## Независимая готовность контекста и поиска

Инициализация проекта, обновление контекста и repair с обновлением контекста
вычисляют или проверяют контекст проекта и наблюдают существующий поисковый
индекс workplace. Первый и повторные вызовы не строят и не перестраивают индекс,
не ставят индексацию в очередь и не ждут её завершения. File-only работа не
требует запущенного PF App Server.

| Состояние | Что оно означает |
| --- | --- |
| Свежесть контекста и готовность обязательных ресурсов | Допускают ли текущие входы проекта и обязательные ресурсы запрошенную работу. |
| Состояние поиска | Доступен ли производный индекс workplace: `missing`, `stale`, `building`, `degraded` или `fresh`. |
| Разрешённое покрытие | Есть ли в индексе ресурсы, выбранные для проекта; физическая свежесть сама по себе не подтверждает полезное покрытие. |

Свежий контекст может сосуществовать с отсутствующим или незавершённым индексом.
Недоступность поиска не отменяет проверки обязательных ресурсов, текущего
доступа, identity Work и ограничений этапа. Если операция требует поиск, эта
зависимость по-прежнему должна быть обеспечена.

Наблюдение читает метаданные каталога и индекса с `verify_files=False`, без
обхода содержимого документов. Проверка контекста продолжает читать необходимые
текущие источники. Проверка выбранного материала Work может читать и хешировать
разрешённые файлы: это проверка доступа и материала, а не индексация документов
всего workplace. Внешние изменения документов обнаруживаются при явной проверке
отпечатков или обслуживании, а не при каждом обновлении контекста.

При недоступном поиске запросите отдельно разрешённое обслуживание workplace:

```bash
python bin/pf.py search-index-maintain --workplace <workplace> --apply --json
```

Контекст проекта и проектная Work не разрешают эту операцию уровня workplace.
Обновление контекста не запускает и не ремонтирует инфраструктуру. Alpha4
предоставляет явный ручной адаптер и холодный callable для будущего планировщика;
периодическое выполнение в Runtime не реализовано. Хранение, команды с областью
проекта и восстановление описаны в [Индексе поиска ресурсов](resource-search-index.md).

Основные пути:

```text
.pf/contexts/project-context.snapshot.yaml
.pf/contexts/project-context.snapshot.md
.pf/contexts/project-context.snapshots/<snapshot-id>.yaml
.pf/runtime/cache/workplace-context.snapshot.yaml
```

Snapshot строится из структурированных источников:

- workplace и project manifests
- process definitions
- package definitions
- tool, MCP, template и specialization registries
- selected specialization definitions и platform bindings
- project overrides
- platform contracts
- source fingerprints
- observed `project_classification` со status, classifier/rule IDs, project
  types, platforms и tags

Snapshot записывает selected platform, platform stack, selected
specializations, active resource profile, execution route, required
capabilities, provided capabilities, capability resolution, applied project
overrides, effective fingerprints и conflicts. Capabilities остаются opaque IDs;
snapshot не разворачивает полный knowledge content.

Snapshot также записывает `resolved_parameters` и `parameter_resolution`.
Параметры собираются только из структурированных источников: workplace
`parameters`, `registries/parameters.yaml`, активных platform/specialization
sources, project manifest, private `overrides.parameters`, `.pf/parameters.yaml`,
`.pf/parameters.local.yaml`, process/stage/task/assignment `parameters` при их
активации. `AGENTS.md` и другие Markdown-инструкции не являются машинными
источниками параметров.

Merge параметров нейтрален к предметной области: maps сливаются рекурсивно,
scalars заменяются более конкретным слоем, списки объектов с `id` сливаются по
`id`, списки без `id` заменяются целиком, `null` удаляет ключ map, а `_delete`
или `__delete__` удаляет элемент списка по `id`.

`capability_resolution` содержит satisfied и unsatisfied requirements. PF core
не удовлетворяет user process capabilities по умолчанию. Если active resource
profile не предоставляет required capability, snapshot фиксирует ее как
`unsatisfied`, а context получает ресурсный conflict/status.

Freshness учитывает specialization definitions, specialization registry,
project specialization overrides, `project-overrides.yaml`, active
tool/MCP/template registries, active project classifiers и результат их
применения, process definition и selected platform contracts.
Existing run/capsule остается pinned; новая сессия должна refresh или сообщить
stale/fresh_with_updates согласно policy.

Runtime workplace snapshot может содержать local availability state для tools и
MCP. Он лежит в `.pf/runtime/cache/` и остается private.

## Конкретное чтение источников

Core `ProjectSnapshotSourcesReader` собирает прежние упорядоченные fingerprints
источников для сборки snapshot и проверки свежести. Каждая операция читает
текущее содержимое; missing records, private display refs, повторные записи и
фильтры расширений сохранены. Ссылка на Workplace manifest из local config
сохраняет прежний контракт разбора raw text. Выбор active official packs общий
для потребителей и принадлежит `OfficialProcessPackReader` с прежней list-only
семантикой реестра.

Reader поставляет входы. Создание и сохранение snapshot, проверка resource
generations, readiness и freshness policy сохраняют своих действующих владельцев.
Он не выдаёт доступ, не обновляет контекст и не изменяет immutable capsules.
Совместимые CLI helpers делегируют Core; схемы snapshot и команды не меняются.
