# Следующие ограниченные срезы

Дата: 2026-10-18. Статус: план основного агента; продуктовая реализация не выполнена. Основание — [исследование topology](../pf121-oop-topology-20261018/report.md), [доменные границы](domain-model.md) и контракт переноса Core от 2026-10-10.

## Первый срез: слияние параметров и provenance

Рекомендуется первым: это связная существующая операция без I/O и новых зависимостей, с конкретным обратным вызовом из `work/context.py` в `core.merge_parameter_maps`. Независимым символическим чтением подтверждено, что текущий merge удаляет ключ при `None`, делает deepcopy и записывает add/delete provenance.

Предлагаемый владелец: `ParameterMergePolicy` в `src/processforge_core/configuration/parameters.py`. Перенести одну группу алгоритмов `parameter_path`, `parameter_list_item_path`, `parameter_list_merges_by_id`, `merge_parameter_value`, `merge_parameter_maps`; согласованные внутренние имена выбрать при admission. Не делать отдельный класс для каждого helper.

Все найденные consumers, включая `add_parameter_source` и `work/context.py::build_context_fields`, переводятся на прямое использование владельца. Удалить старую реализацию и ненужные внутренние aliases. При этом `build_context_fields` в целом остаётся неперенесённым сценарием: другие legacy-зависимости не следует скрывать или объявлять устранёнными.

Контракт: прежние значения и native errors; `None` как удаление; строковые ID и условия объединения списков; порядок, дубликаты, delete-маркеры; defensive copies и мутация переданного provenance; отсутствие изменения входов вне существующего контракта. Не исправлять попутно некорректные входы и не менять null-as-inherit в другом resolver.

Новый Work должен ограничить запись новым модулем, `tools/processforge.py`, `src/processforge_core/work/context.py`, непосредственно затронутой текущей документацией и shipped checksum inventory, а также собственными artifacts/scratch. Сначала проверить отсутствие активного пересекающегося writer. Прямые публичные CLI/MCP entrypoints, schemas и payloads сохраняются.

Порядок выполнения:

1. Перечитать исходные specs/ADR/domain/direction, контракт переноса и `src/processforge_core/AGENTS.md`; получить PF Python knowledge через точный work-resolve.
2. Зафиксировать все реальные consumers и baseline существующих проверок до изменений.
3. Перенести алгоритм и обновить всех callers одним writer. Ни старый callback, ни внутренний compatibility alias не сохраняются ради переноса.
4. Проверить normal default use нового владельца без импорта CLI/Host и сравнить значения, ошибки, provenance и порядок на содержательных существующих случаях; небольшие временные parity fixtures держать в `.pf/tmp` нового Work.
5. Выполнить относящиеся существующие parameter cascade, assignment capsule и freshness проверки. Не добавлять постоянный набор тестов только ради перемещения и не запускать полный release suite без причины.
6. После завершённой реализации провести независимое ревью с чистым контекстом, разрешить замечания и согласовать evidence. Обновить текущую карту владения и checksum inventory, если затронуты поставляемые файлы.
7. Завершить native lifecycle, отдельный коммит результата и обе dev-доставки с readback одинакового полного SHA. Archive/installed/Runtime/connected acceptance отмечать только при фактической отдельной проверке.

Затрагиваются D01/D02/D06/D07/D09/D11 исходного ADR и R01–R07/R10–R12 при использовании операции компилятором контекста. Перенос не вводит новый Kernel, DI runtime, extension API или права доступа. Поведенческие измерения относятся только к проверенному корпусу.

## Вторая и третья ротации

| Очередь | Ответственность и предлагаемый владелец | Границы и проверки |
| --- | --- | --- |
| 2 | `ProjectClassifierRulePolicy`, `project/classification.py`; общий matcher в `common/paths.py` | Перенести существующие condition/rule matchers и всех callers общего matcher. Сохранить `all`/`any` precedence, short circuit, basename/slashes и платформенное поведение `fnmatch.fnmatch`. Registry/activation и обход дерева не входят. Проверки classification, inventory pruning, official pack и scan boundaries. |
| 3 | `ProcessArtifactDeclarationPolicy`, `process_catalog/artifacts.py` | Перенести существующий расчёт defined/declared/produced IDs и обновить authoring, contract validator и builtin catalog consumers. Полный validator и companion-file reads не входят. Сохранить позднюю семантику `as_list`: scalar даёт пустой список, а не singleton. Проверки malformed деклараций, duplicates, ID conversion и stage/catalog contracts. |

У всех трёх срезов есть общий writer-файл `tools/processforge.py`. Поэтому выполнять их последовательно. Разные диапазоны строк одного файла не являются непересекающимися областями. Нельзя выдавать эти три полные реализации параллельным writers.

## Отдельные будущие изменения

Мастер установки, новый MCP resource transport, расширения tools, сбор RSS/private/USS и изменение санитизации/квоты operator log требуют самостоятельной оценки и разрешённого scope. Извлечение существующего поведения setup или operator log возможно как рефакторинг, но оно не должно незаметно добавлять эти возможности.

Расхождения текущего справочника Core (общая retention YAML-разбора, актуальные factory parameters) можно исправить отдельным документальным срезом. Исторические approved планы и immutable capsules остаются неизменными.

Handoff: это приоритеты и проверяемые границы, а не уже созданные backlog cards. Перед новой Work проверить существующие assignments и ownership; не дублировать открытые OOP-эпики. После завершения данного исследовательского результата соблюдается проектная граница остановки на завершённой задаче.
