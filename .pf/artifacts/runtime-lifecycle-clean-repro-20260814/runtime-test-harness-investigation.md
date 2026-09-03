# runtime-test-harness-investigation

## Итоги проверки

- В текущих smoke-скриптах для задания temp-workspace используется `tempfile.TemporaryDirectory(...)` без явного `dir`:
  - `tools/smoke_long_lived_runtime.py:144`
  - `tools/smoke_runtime_ledger_hooks_mcp.py:44`
  - `tools/smoke_verification_current_work_state.py:42`
- В мастере воспроизведения (`задания/...`) зафиксировано:
  - сценарий падения `PermissionError (WinError 5)` на этапе temp workspace/`init-workplace`
  - проброс возможных корней: `D:\Temp`, `TEMP/TMP`, `.pf/runtime/verification-temp`
- Значит проблема появляется до старта Runtime, на уровне выделения временного каталога, а не внутри бизнес-логики runtime.

## Классификация `PermissionError` (без изменений runtime/prod/smoke-кода)

- Тип: блокирующий инфраструктурный блокер test-harness (Windows ACL / sandbox policy / filesystem policy).
- Уровень: **environmental / platform** (внешняя среда запуска), не кодовый дефект `runtime`.
- Признак: `WinError 5` на создании/инициализации каталога в temp-хранилище при `tempfile.TemporaryDirectory`, до вызова `workplace-init`.

## Минимальная durable Windows temp-root matrix

### 1) Операционный профиль (для каждого корня)
- Создание каталога (`mkdir`)
- Создание файла-маркера (`write`)
- Чтение файла (`read`)
- Переименование/перемещение (`rename`)
- Удаление (`delete`)

### 2) Корни и ожидания

| Candidate root | Temp API | Create | Marker write/read | Rename | Delete | Итог (стабильность) |
|---|---|---|---|---|---|---|
| `tempfile.gettempdir()` (`TEMP/TMP`, в т.ч. `D:\Temp`) | `tempfile.TemporaryDirectory()` | ❌/⚠ | - | - | - | Нестабильно на Windows при ACL/антивирус/локи |
| `repo/.pf/runtime/verification-temp` | `tempfile.TemporaryDirectory(dir=...)` + `mkdir` fallback | ✅ | ✅ | ✅ | ✅ | Стабильно при подготовленном writable пути |
| `repo/.pf/runtime/test-temp` | `tempfile.TemporaryDirectory(dir=...)` + `mkdir` fallback | ✅ | ✅ | ✅ | ✅ | Стабильно; изолированный project-local root |
| `repo/.tmp` | `tempfile.TemporaryDirectory(dir=...)` + `mkdir` fallback | ✅ | ✅ | ✅ | ✅ | Стабильно; простой fallback |
| `repo/.pf/runtime/test-temp/<run-id>` (детерминированный) | `pathlib.Path().mkdir()` + `mkdtemp(dir=...)` | ✅ | ✅ | ✅ | ✅ | Максимально детерминированный и изолированный вариант |

### 3) Рекомендованный порядок тестирования
- `repo/.pf/runtime/verification-temp`
- `repo/.pf/runtime/test-temp`
- `repo/.tmp`
- только при успешном probe предыдущих — `tempfile.gettempdir()` как fallback
- на каждом шаге: `create/mkdir -> write -> read -> rename -> delete`, логировать любой отказ с кодом/путём.

## Рекомендуемый вывод

- `PermissionError` следует классифицировать как **`Infrastructure/Temporary-Filesystem Blocker`**, а не как regression runtime lifecycle.
- Дальнейшее снятие blocker-эффекта нужно реализовать через **явный, проверенный temp-root (локально-проектный) в harness**, а не через default Windows TEMP.