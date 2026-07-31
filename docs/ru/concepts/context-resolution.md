# Вычисление контекста

Вычисление контекста превращает входы workplace, проекта, процесса, пакетов,
шаблонов, инструментов и assignment в небольшой набор файлов, с которым worker
может работать без повторного чтения всего репозитория.

Структурированные `parameters` вычисляются как данные, а не как инструкции.
`AGENTS.md` и другие Markdown-рекомендации не разбираются как машинные источники
параметров.

## Результаты

Resolver создаёт:

- Context Index: точный список источников и fingerprints;
- Resolved Rules: объединённые инструкции, сгруппированные по типам политик;
- Conflict Report: blocked, warning, approval и resolved conflicts;
- опциональный Execution Context Package для assignment;
- опциональную Context Capsule для запуска worker.

## Порядок источников

ProcessForge использует каскадную модель:

1. core
2. workplace
3. organization
4. direction
5. specialization
6. platform
7. toolchain
8. project
9. process
10. stage
11. task
12. agent profile

Более локальные слои могут сужать или расширять поведение, но не могут ослаблять
locked hard policies.

Для значений параметров первый обязательный машинный слой - `workplace`.
Organization и direction являются опциональными. Локальный station/global layer
может участвовать только тогда, когда он явно настроен как структурированные
данные; обычные глобальные инструкции агента не входят в parameter resolution.

## Классификация правил

Перед объединением правила классифицируются:

- `hard`: нельзя ослаблять или игнорировать;
- `locked`: нельзя переопределить нижележащим слоем;
- `preference`: может быть заменено более локальным слоем;
- `gate`: управляет входом, выходом или approval;
- `tool`: выбирает или ограничивает инструменты и capabilities;
- `template`: выбирает формы повторно используемых артефактов.

Resolver не должен склеивать все инструкции как простой Markdown. Он записывает
класс и источник каждого правила, чтобы конфликты можно было объяснить.

## Вычисление параметров

Parameter resolver объединяет активные структурированные блоки `parameters` в
том же каскадном порядке. Он одинаково относится ко всем namespaces:
platforms, toolchains, specializations, processes, projects и tasks могут
добавлять параметры, когда их структурированный источник активен. Resolver при
этом не знает предметного смысла параметров.

Snapshot записывает `resolved_parameters` и metadata `parameter_resolution`:
источники, provenance, status и conflicts.

Для project snapshots вычисление параметров начинается со слоя workplace.
Глобальный файл инструкций агента намеренно находится вне этого машинного merge.
Если команде нужны station-level parameters выше workplace, их нужно явно
предоставить как структурированный источник параметров; обычный Markdown
остаётся подсказкой для человека или агента.

Текущие источники project snapshot:

- workplace `parameters`;
- `registries/parameters.yaml`;
- параметры активной platform;
- параметры активной specialization;
- project manifest `parameters`;
- local `overrides.parameters`;
- `.pf/parameters.yaml`;
- `.pf/parameters.local.yaml`.

Assignment capsules добавляют assignment `parameters` поверх закреплённого
project snapshot.

Алгоритм merge близок к registry-модели: maps объединяются рекурсивно, scalars
заменяются, lists of maps with `id` объединяются по `id`, lists without ids
заменяются целиком, `null` удаляет map key, а `_delete` или `__delete__`
удаляет list item по `id`.

## Минимальное поведение CLI

```bash
python bin/pf.py context-resolve --project-root <path>
```

Команда записывает context index, resolved rules, conflict report и приватный
cache record. Она работает консервативно: отсутствие обязательных источников
или blocking conflicts не дают получить чистый context status.

См. также [каскадное объединение](cascade-merge.md),
[snapshot проектного контекста](project-context-snapshot.md) и
[lock-модель проектного контекста](project-context-lock-model.md).
