# Постизмененная характеристика Phase C (каталог/resolve seam)

## Цель проверки
Проверить сборку/помощь CLI, `ProcessDefinitionRef`, доступные smoke-проверки для каталога/resolve и целостность `git diff` без изменений продукта.

## Результаты команд

### 1) Compile check
- Команда:
  `python -m compileall -q tools/pf_runtime/host.py tools/processforge.py src/processforge_core`
- Результат: `exit code 0` (проверка синтаксиса прошла успешно)

### 2) CLI help (direct + bin/legacy)
- Direct script:
  - `python tools/processforge.py --help`
    - Результат: `exit code 0`, сформирован полный список команд.
- Модульный запуск:
  - `python -m tools.processforge --help`
    - Результат: `ModuleNotFoundError: No module named 'processforge_subprocess'`.
- Прямой CLI-импорт:
  - `python -m processforge --help`
    - Результат: `No module named processforge`.
- Поиск бин-CLI:
  - `Test-Path .\bin\processforge.py` → `False`
  - `Test-Path .\bin\pf.py` → `True` (сейчас релевантный бинарный вход — `bin/pf.py`)
  - `python .\bin\pf.py --help`
    - Результат: `exit code 0`, help корректно отрисован.
  - `.\bin\pf.bat --help`
    - Результат: `exit code 0`, help корректно отрисован.

### 3) `ProcessDefinitionRef` identity (состояние и семантика)
- Файл: `src/processforge_core/process_catalog/models.py`
  - `ProcessDefinitionRef` — `@dataclass`, `frozen=False`, `eq=True`.
  - Поля:
    - `process_id`, `path`, `process`, `origin`, `root`, `catalog_role`, `warnings`,
      `pack_id` (по умолчанию `""`), `active` (`True`), `available` (`True`), `production_ready` (`False`).
- Runtime-резолвер:
  - `tools/pf_runtime/host.py`: `resolved_process()` вызывает `resolve_process_definition_core(...)` и в кэш кладёт кортеж `(definition.path, mtime, definition.process)`.
  - Возвращает `definition.process` (dict), а не объект `ProcessDefinitionRef` целиком.

Вывод: `ProcessDefinitionRef` используется как value-dataclass для каталога и резолва, но на уровне runtime-хоста в кэше хранится только словарь процесса; это важно для ожиданий по идентичности ссылок/жизненному циклу объекта.

### 4) Доступные и прогнанные resolver/catalog smoke
- Доступные файлы по паттернам `smoke_*process*.py`:
  - `tools/smoke_builtin_process_catalog.py`
  - `tools/smoke_core_process_catalog_domain_neutral.py`
  - `tools/smoke_process_resolver_multiple_roots.py`
  - а также ряд др. process/process-resolve смоков.
- Выполненные smoke:
  - `python tools/smoke_core_process_catalog_domain_neutral.py` → `PASS: smoke_core_process_catalog_domain_neutral` (`exit code 0`)
  - `python tools/smoke_builtin_process_catalog.py` → `exit code 1`
    - Причина: команда `builtin-process-catalog-doctor --root ...` завершается с кодом 1 (см. диагностику в выводе; нет успеха из-за текущих ворнингов/режима, не из-за отсутствия команды).
  - `python tools/smoke_process_resolver_multiple_roots.py` → `exit code 1`
    - Причина: `PermissionError` при `tempfile.TemporaryDirectory(...)/...pf-process-roots-...` и последующем `cleanup` в `D:\temp\...` (доступ отсутствует).

### 5) Git diff check
- Команда:
  - `git diff --check -- .pf/artifacts/python-core-refactor-phase-c-20260814/postchange-characterization.md`
- Результат: без предупреждений (нет конфликтов пробелов/отступов в целевом артефакте).

## Ресурсы/остаточные ограничения
- Проверка смоков подтверждает, что seam каталога/resolve покрыт несколькими активными целями, но один smoke-файл падает из‑за системных ограничений временной папки (`D:\temp`), второй — из‑за non-zero поведения `builtin-process-catalog-doctor` в текущем контексте.
- Работа с `python -m tools.processforge --help` нестабильна в текущем layout (`processforge_subprocess` вне модуля).