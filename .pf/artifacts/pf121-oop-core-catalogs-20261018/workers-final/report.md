# Отчёт workers

Статус: **вклад готов к интеграции**. Реализован `WorkerPlanPolicy` в `src/processforge_core/runtime/worker_plans.py`. Общая приёмка среза остаётся за primary.

## Контекст и границы

Проверены точные идентификаторы:

- Run: `garage-p121-core-catalogs-v2-workers-create-workerplanpolicy-with-eight`.
- Assignment: `p121-core-catalogs-v2-workers-create-workerplanpolicy-with-eight-mapped`.
- Context: `p121-core-catalogs-v2-workers-create-workerplanpolicy-with-eight-mapped-capsule`.

Source `work-state` подтвердил `valid`, `ready`, стадию `implementation`, отсутствие blockers и наличие implementation-plan. SHA-256 capsule совпал с подготовленным входом.

Прочитаны объявленные архитектурные входы, brief, handoff, Core AGENTS, Python material и конкретные зависимости. Замороженные функции сверены с Git baseline `3d5a01b10463ce119fc83bc513aff74386690816`; после восстановления CRLF исходный файл совпал с pinned `source_sha256`.

## Изменение

| Исходная функция | Метод WorkerPlanPolicy |
|---|---|
| `worker_subagent_policy` | `subagent_policy` |
| `default_orchestrator_task_plan` | `default_task_plan` |
| `plan_worker_map` | `worker_map` |
| `task_dependency_ids` | `task_dependency_ids` |
| `task_dependencies_done` | `task_dependencies_done` |
| `worker_dependency_set` | `dependency_set` |
| `worker_depends_on` | `depends_on` |
| `plan_allows_write_scope_overlap` | `allows_write_scope_overlap` |

Используются конкретные `ContextContractInputs`, `WorkPaths` и `YamlDocumentReader(_parse_simple_yaml)`. Конструктор не выполняет I/O.

Сохранены строгий `documents.read`, текущие пути и статусы assignment, порядок guards/read и ранний `False`; нормализация идентификаторов, alias identity значений worker map, литералы default plan, объединение зависимостей, `seen = seen or set()`, общий рекурсивный набор и проверка `is True`.

## Доказательства

В каталоге `.pf/artifacts/pf121-oop-core-catalogs-20261018/workers-final/`:

- `proof.py` — воспроизводимая ограниченная проверка.
- `proof.json` — полный нормализованный AST каждого метода, signatures и фактические `__annotations__` обеих реализаций.
- `log.md` — журнал действий и оставшихся проверок.
- `changed-files.json`, `hashes.json` — перечень изменений и raw hashes.

Для **8/8 методов** подтверждено полное равенство AST после исключительно объявленных преобразований: удаления формального `self`, обратного отображения имён методов и замены обращений к конкретным зависимостям исходными именами. Совпали bound signatures, фактические annotations и `from __future__ import annotations`.

Выполнены **пять синтетических случаев**, все `passed`:

1. Нормализация subagent policy, override, native ValueError/TypeError и causes, точные default literals и независимость вложенных значений.
2. Нормализация worker id, last-wins, alias identity и видимость мутаций.
3. Объединение зависимостей, преобразование/filter/sort и буквальная идентичность `True`.
4. Циклы, прямые/транзитивные зависимости, отсутствующие workers и мутации `seen`.
5. Трассировка текущих assignment reads, ранний `False`, точный YAML `SystemExit` и повторное чтение изменённого статуса.

Новые и изменённые файлы заканчиваются ровно одним newline.

## Архитектурное соответствие и передача

D01/D02/D03/D06/D09/D11 сохранены в пределах ответственности: реализация принадлежит Core, зависимости конкретные, обратных вызовов монолита и новых framework-механизмов нет. Затронутые аспекты R01–R12 сохранены без изменения lifecycle, permissions, locks, recovery или execution.

Primary остаются миграция consumers, проверка actual default composition, live fixtures, существующие affected smokes и независимое review. Здесь suites, инфраструктурные действия, Git/remote mutations, nested agents и lifecycle transitions не выполнялись.

## Итоговые raw SHA-256

| Файл | SHA-256 |
|---|---|
| `src/processforge_core/runtime/worker_plans.py` | `a10cc5ed53bc475cbd31dfa198183e62cc23281783a43f602ab2d798c8759ac0` |
| `proof.py` | `e689e04b5ff076e30e056ac43ae56e386048be11c8f0ee893e2116101273e5ad` |
| `proof.json` | `c911fed34b7e635cfd17db1630815bead1f2e3bf73923ccca0b6e74265ed6a58` |
| `log.md` | `55aaf06b40029c17c9ea173f2249f48fa22d047fe561a5775bedf823e20e1fd3` |
| `changed-files.json` | `8f6e9555a4e608fc9d2083bb40fb78b982fd9c1303e0f68527e2536b86df84b5` |
| `hashes.json` | `d02353bfb431dcdacc91dc5f92f48c775b87474f7c023c454b4324b8a8d23597` |