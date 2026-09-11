# Отчёт аудита ядра ProcessForge

Дата: 2026-09-11  
Базовый commit: `901d0551773fe7a5b382b89ebe95b212b0747e83`  
Охват: `src/processforge_core/core_update.py`, `src/processforge_core/local_resource_search.py`, CLI-контракты.

## Итог

Обнаружены две воспроизводимые проблемы высокой ценности. Product-код не изменялся.

## F-CORE-01 — отсутствующий источник миграции оставляет update в состоянии `applying`

- Severity: High
- Файл: `src/processforge_core/core_update.py:272-276`, `:321`, `:583-612`
- Статус: подтверждено предыдущим запуском; повторный запуск в текущей песочнице заблокирован `PermissionError` при создании временной директории.

### Нарушенный контракт

Документация требует, чтобы ошибки файловых операций преобразовывались в структурированную ошибку и сохраняли journal со статусом `failed` (`docs/concepts/core-update-manifest.md:86-99`).

### Триггер

ZIP-архив содержит валидную Workplace migration с операцией:

```yaml
type: copy_if_missing
source: templates/missing.yaml
target: runtime-drivers/missing.yaml
```

Файл `templates/missing.yaml` отсутствует в архиве.

### Ожидаемое поведение

Планирование должно отклонить архив структурированной ошибкой до создания update state либо применение должно записать `status: failed`.

### Фактическое поведение

`build_plan()` возвращает успешный план. Затем `archive.read()` выбрасывает сырой `KeyError`. Обработчик `apply_update()` не перехватывает `KeyError` и оставляет `in-progress.json` со статусом `applying`.

### Воспроизводитель

```powershell
python .pf/artifacts/codebase-audit-20260910/native-core/audit_core_update_missing_migration_source.py
```

Сохраненный результат:

```text
PLAN_STATUS planned
MIGRATION_STATUS planned
APPLY_EXCEPTION KeyError KeyError("There is no item named 'templates/missing.yaml' in the archive")
IN_PROGRESS_EXISTS True
IN_PROGRESS_STATUS applying
```

### Воздействие

Оператор видит незавершённое обновление без структурированной причины. Последующие обновления блокируются ложным состоянием incomplete update; восстановление требует ручного вмешательства.

### Минимальное исправление

Во время `workplace_migration_plan()` проверить наличие каждого `copy_if_missing.source` среди ZIP members и, желательно, среди manifest-owned files. Дополнительно обработать `KeyError` как структурированную ошибку обновления с записью `status: failed`.

### Изолированная remediation-задача

Разрешённые файлы:

- `src/processforge_core/core_update.py`
- новый smoke-тест в `tools/`

Acceptance checks:

- отсутствующий migration source отклоняется до применения;
- результат содержит структурированный код ошибки;
- `in-progress.json` не остаётся со статусом `applying`;
- Workplace не изменяется.

Сложность: S. Рекомендуемая модель: junior coding model.

## F-SEARCH-02 — single-file resource root позволяет индексировать соседний файл через `..`

- Severity: High
- Файл: `src/processforge_core/local_resource_search.py:352-369`
- Статус: подтверждено предыдущим запуском; повторный запуск в текущей песочнице заблокирован `PermissionError` при создании временной директории.

### Нарушенный контракт

По документации индекс должен читать только явно разрешённые resource roots и declared sources (`docs/concepts/resource-search-index.md:3-7`, `:25-51`).

### Триггер

Authorized resource имеет `content_roots`:

```text
/project/allowed.md
```

Источник указывает:

```text
../secret.txt
```

Проверка использует `root.parent` для file-root, поэтому соседний файл считается допустимым.

### Ожидаемое поведение

Источник должен быть ограничен самим авторизованным файлом; внешний путь должен дать нулевой результат либо структурированную ошибку.

### Фактическое поведение

Соседний файл обнаруживается, индексируется и возвращается поиском.

### Воспроизводитель

```powershell
python .pf/artifacts/codebase-audit-20260910/native-core/audit_search_file_root_escape.py
```

Сохраненный результат:

```text
DISCOVERED [('...\\project\\secret.txt', 'secret.txt')]
INDEXED {'status': 'fresh', 'indexed': 1, 'resources': 1, ...}
SEARCH_TOTAL 1
RESULT_PATHS ['secret.txt']
```

### Воздействие

Политика авторизации ресурса обходится через относительный путь. Поиск может раскрыть содержимое sibling-файлов, не входящих в разрешённый resource.

### Минимальное исправление

Для file-root разрешать только `base == root`. Для directory-root сохранить проверку `base.relative_to(root)`. Добавить отдельную проверку explicit-file source до индексации.

### Изолированная remediation-задача

Разрешённые файлы:

- `src/processforge_core/local_resource_search.py`
- новый smoke-тест в `tools/`

Acceptance checks:

- `../secret.txt` не обнаруживается;
- индекс не содержит sibling-файл;
- поиск уникального маркера sibling-файла возвращает `total == 0`;
- обычный explicit authorized file продолжает индексироваться.

Сложность: S. Рекомендуемая модель: junior coding model.

## Проверки

- Существующие smoke-тесты были проанализированы.
- Повторный запуск probe/smoke в текущей среде невозможен: Windows sandbox возвращает `PermissionError: [WinError 5]` при создании каталогов в системном `%TEMP%`.
- Предыдущие captured outputs и воспроизводители сохранены в `.pf/artifacts/codebase-audit-20260910/native-core/`.
- Product-код и другие assignment-файлы не изменялись.