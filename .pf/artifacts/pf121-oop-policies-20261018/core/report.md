# Отчёт Core: classifier и artifact policies

Статус: реализация Core завершена; готово к передаче consumer owner. Lifecycle-переходы остаются за main.

## Идентичность и допуск

- Project: `process-forge`.
- Run: `garage-p121-policies-core-implement-the-two-existing-pure-responsibiliti`.
- Assignment: `p121-policies-core-implement-the-two-existing-pure-responsibilities-in-o`.
- Context: `p121-policies-core-implement-the-two-existing-pure-responsibilities-in-o-capsule`.
- Проверено точное `work-state` через существующий source CLI: стадия `implementation`, context `valid`, readiness `ready`, blockers отсутствуют. Вход `implementation-plan` удовлетворён frozen brief.
- SHA-256 capsule, snapshot и brief совпадают с prepared input. Прочитаны inline brief, правила Core, assignment, capsule, baseline-functions.json; тела ресурсов с доступом только к метаданным не читались.

## Изменённые файлы и результат

Переносы выполнены последовательно:

1. Создан `src/processforge_core/project/classification.py`: обычный stateless-класс `ProjectClassifierRulePolicy`, публичный instance-метод `matches(rule, available_paths) -> bool`, приватный `_condition_matches(condition, available_paths)`. В существующий `src/processforge_core/common/paths.py` перенесён `path_matches_pattern(path, pattern) -> bool`; исходный текст `rel` сохранён.
2. Создан `src/processforge_core/process_catalog/artifacts.py`: обычный stateless-класс `ProcessArtifactDeclarationPolicy` с instance-методами `defined_ids(process)`, `declared_ids(process)`, `produced_ids(process)`, возвращающими `set[str]`. Приватные `_as_list` и `_string_list` сохраняют эффективную позднюю семантику монолита; любое значение, кроме списка, преобразуется `_as_list` в `[]`.

Сохранены приоритет списка `all`, включая пустой, short circuit, проверки форм данных, нормализация обратных слешей, стандартная платформенная семантика `fnmatch`, проверка полного пути и basename, truthiness ID, устранение дубликатов, порядок преобразований и native errors. Новые владельцы не импортируют монолит или `process_catalog.service`, не используют callbacks или compatibility aliases.

## Проверка

- Компиляция трёх файлов в памяти и прямой импорт публичных API: успешно, без загрузки монолита.
- 9 сравнений AST с frozen baseline: успешно. Нормализация ограничена именами новых API/приватных helpers и заменой вызовов на instance-методы. Отдельно подтверждено точное совпадение исходного текста `rel`.
- 147 сравнений поведения с baseline: успешно. Проверены результаты и типы/сообщения исключений, неверные формы, пустой `all` с непустым `any`, short circuit с исключением в недостижимом условии, slash/basename/case matching, scalar/list/dict artifact declarations, ложные и повторные ID, comma-separated строки и наблюдаемый порядок вызовов `str`.
- `git diff --check` по разрешённым продуктовым путям: успешно.
- Первоначальная дополнительная проверка отсутствия `process_catalog.service` в `sys.modules` оказалась неприменима: существующий package import загружает service. Проверка уточнена до зависимостей самих новых владельцев; обращения к service отсутствуют. Продуктовый код ради проверки не менялся.
- Постоянные тесты, временные fixtures и широкие проверки не создавались и не запускались. Интеграционные smokes и независимая QA остаются за main/QA согласно brief.

SHA-256 продуктовых файлов:

| Файл | SHA-256 |
| --- | --- |
| `src/processforge_core/common/paths.py` | `19b5bfecb8506f68a5efe7e5dcca34851b3b638bc14c83cabe89aac324f9ae56` |
| `src/processforge_core/project/classification.py` | `22b8865a70a03390d379afed9853afb1bc12f0ee831875e91d6ad3ec63d10b00` |
| `src/processforge_core/process_catalog/artifacts.py` | `7ab9b30545e08e4db688760be8099ccae707c2ebd6621492b65d1449ece8a2a6` |

## Журнал

- 2026-10-18 17:34:47 UTC, worker-p121-policies-core: завершён первый перенос. Создан `src/processforge_core/project/classification.py` с `ProjectClassifierRulePolicy.matches` и приватным `_condition_matches`; в `src/processforge_core/common/paths.py` добавлен исходный `path_matches_pattern`. Проверены компиляция в памяти и неизменность AST `rel`; `git diff --check` прошёл. Serena использована для адресного чтения исходных символов. Следующий шаг: artifact policy, затем ограниченная проверка и передача consumer owner.
- 2026-10-18 17:36:24 UTC, worker-p121-policies-core: завершён второй перенос в `src/processforge_core/process_catalog/artifacts.py`; ограниченные AST/parity/import проверки прошли. Последующая проверка подтвердила исходный текст `rel`, чистый diff по whitespace и приведённые SHA-256. Статус: готово к передаче; pending — миграция callers, интеграционные smokes, QA и review.

## Передача

Consumer owner должен последовательно мигрировать в `tools/processforge.py` обе группы: сначала classifier callers и общую path primitive, затем artifact callers; удалить шесть старых определений: три classifier/matcher и три artifact helpers. Генерические `as_list`/`string_list` оставить для остальных потребителей. Все caller edits оставлены consumer owner.

Записи ограничены тремя продуктовыми файлами и этим отчётом. Git mutations, remote access, infrastructure changes, nested agents, context rebuild и lifecycle transitions не выполнялись. Блокеров реализации Core нет; интеграционная завершённость и завершение Run не заявляются.