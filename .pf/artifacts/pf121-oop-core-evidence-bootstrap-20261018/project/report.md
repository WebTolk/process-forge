# Отчёт project

Статус: **passed** в границах worker-задания.

Assignment: `p121-core-evidence-bootstrap-project-create-project-initialization-input`  
Run: `garage-p121-core-evidence-bootstrap-project-create-project-initializatio`  
Context: `p121-core-evidence-bootstrap-project-create-project-initialization-input-capsule`

Проверены identity, контрольная сумма капсулы, process pin, этап `implementation`, readiness `ready` без блокеров и контрольные суммы 31 закреплённого источника. Архитектурные входы, brief, PF Python material и полные frozen inputs прочитаны.

## Изменения

Создан `src/processforge_core/project/initialization_inputs.py` с классом `ProjectInitializationInputs` и двумя точными исходными присваиваниями `PROCESSFORGE_CORE_PROJECT_TYPES` / `META_PROJECT_TYPES`. Используется канонический `common.ids.safe_id`; конструктор холодный, корни передаются явно.

В `src/processforge_core/project/initialization.py` добавлен канонический импорт и заменён единственный вызов `core.project_mode(...)` на `ProjectInitializationInputs().mode(...)`. Остальные байты consumer сохранены.

## Доказательства сохранения

Сравнение полного AST допускает только объявленные переименования, добавление `self` и замену владельца внутреннего вызова.

| Исходный алгоритм | Метод | full_ast_equal | signature_equal | annotations_equal |
|---|---|---|---|---|
| `project_types_from_manifest` | `types_from_manifest` | true | true | true |
| `project_type_allows_processforge_core` | `allows_core` | true | true | true |
| `project_type_is_meta_workspace` | `is_meta_workspace` | true | true | true |
| `project_mode` | `mode` | true | true | true |
| `project_defaults` | `defaults` | true | true | true |

Обе константы имеют `full_ast_equal: true`.

Для consumer `initialization.py` подтверждены:

- `full_ast_equal: true`
- `raw_only_declared_changes: true`
- `assertions_unchanged: true`
- `fixtures_unchanged: true`
- `no_eager_bootstrap_regression: true`

Guard/plan/apply lambdas, порядок проверок и эффектов, поля результатов и невыбранное поведение сохранены. Контракты `ProjectCoordinationReader` и строки JSON `project_mode` не изменялись.

## Проверки

Компиляция обоих продуктов без импорта продуктов: **passed**.

Ровно пять синтетических дифференциальных случаев, каждый выполнен один раз:

1. Manifest: повторные `get`, truthiness, порядок, фильтрация и дубликаты.
2. Пересечения типов Core/meta с сохранением входных данных.
3. Явный режим до любого обращения к корню.
4. Автоматический режим: порядок обхода и исходный `NotADirectoryError` без изменения identity или cause.
5. Defaults: приоритет `auto`, повторное индексирование `project_kind` и сохранение alias.

Все случаи: **passed**. Полное нормализованное AST дополнительно подтверждает неизменность остальных ветвей и литералов.

## Контрольные суммы продуктов

| Путь | SHA-256 исходных байтов |
|---|---|
| `src/processforge_core/project/initialization_inputs.py` | `85477d552de41272ae0c7b2b1f82d7a2131917253af0ac202f059737537c27ca` |
| `src/processforge_core/project/initialization.py` | `58c9b3033e3dac7dc86ffb65be3bfd5737742d88678c3871dc1212e259aaf419` |

`prior_owners` содержит только неизменённую каноническую зависимость `src/processforge_core/common/ids.py`: `raw_equal: true`, `ast_equal: true`, SHA-256 `ad4c6d38a0ba4a2da2cae741a02da7a2cd6229f65386bd7b29c1d864c1e356b8`.

Evidence в `.pf/artifacts/pf121-oop-core-evidence-bootstrap-20261018/project/`: `proof.json` со статусом `passed`, `normalized-ast.json`, `verified-inputs.json`, `verify.py`, `execution-log.md`. Продукты завершаются ровно одним переводом строки.

Serena/IDE недоступны; применён файловый fallback. Реальные scratch-проверки, default composition, copied Core, affected scripts, миграция Main и lifecycle transitions передаются основному агенту. Git mutations, remote access, инфраструктурные действия и вложенные агенты не выполнялись.
