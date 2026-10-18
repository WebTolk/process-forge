# Отчёт consumers

Дата: 2026-10-18  
Роль: worker-p121-policies-consumers  
Статус: реализация завершена; готова к проверке основным агентом.

## Контекст

Проверены обязательные inline-входы brief и Core AGENTS, immutable capsule и текущее состояние assignment: `implementation`, `in_progress`. SHA-256 capsule совпадает с prepared input. Идентификаторы assignment, run и context согласованы.

## Изменения

Изменён только `tools/processforge.py`, строго в заданном порядке:

1. Перенесены два вызова правил в `inactive_official_classifier_hints` и `classify_project` на `ProjectClassifierRulePolicy.matches`. Matcher импортирован непосредственно из `processforge_core.common.paths`; существующие вызовы в `detection_group_matches` и `platform_detection_matches` используют этот импорт.
2. Перенесены четыре вызова на `ProcessArtifactDeclarationPolicy.declared_ids` и три на `produced_ids`: authoring, проверка контракта процесса и builtin catalogue.

Обе политики импортированы из модулей-владельцев. Удалены все шесть прежних определений. Оба определения `as_list` и определение `string_list` сохранены без изменений. `fnmatch` сохранён для остальных потребителей.

## Проверки

Успешно выполнены:

- Синтаксическая компиляция в памяти после каждого переноса.
- Проверка AST импортов и наличия требуемых методов Core.
- Проверка отсутствия удалённых определений и устаревших обращений.
- Сравнение AST: пять изменённых функций отличаются только заменой вызываемых функций; остальные узлы верхнего уровня, кроме импортов, удалённых функций и двух новых экземпляров политик, сохранены.
- Отдельная проверка неизменности `as_list`, `string_list` и обеих функций detection.
- `git diff --check` и просмотр diff.

Исходные CRLF сохранены. Git сообщил о настроенной нормализации CRLF в LF; ошибок whitespace нет. Для анализа использованы Serena и ограниченные локальные AST/текстовые проверки.

## Контрольные суммы SHA-256

| Файл | SHA-256 |
|---|---|
| `tools/processforge.py` | `ebd867d78eca02239112f8d2eee4b027b5d58509d1a9784453f6b2e22433a2ac` |
| `src/processforge_core/project/classification.py` | `22b8865a70a03390d379afed9853afb1bc12f0ee831875e91d6ad3ec63d10b00` |
| `src/processforge_core/common/paths.py` | `19b5bfecb8506f68a5efe7e5dcca34851b3b638bc14c83cabe89aac324f9ae56` |
| `src/processforge_core/process_catalog/artifacts.py` | `7ab9b30545e08e4db688760be8099ccae707c2ebd6621492b65d1449ece8a2a6` |

## Передача

Блокеров реализации не обнаружено. Поведенческие проверки, smoke-наборы и полные suites не запускались согласно заданию; подтверждение поведения остаётся за основным агентом и QA.

Git-мутации, удалённый доступ, инфраструктурные изменения, вложенные агенты и переходы lifecycle не выполнялись. Native transitions выполняет основной агент.