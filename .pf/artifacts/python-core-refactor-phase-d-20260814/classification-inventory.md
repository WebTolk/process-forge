## Инвентаризация `PROCESS_CATALOG_CLASSIFICATIONS` / `process_catalog_metadata` (Python Core, Phase D)

### 1) Legacy‑определения, которые ещё есть

- `src/processforge_core/process_catalog/service.py`
  - `PROCESS_CATALOG_CLASSIFICATIONS` — строки ~`11-16`
  - `process_catalog_metadata(...)` — строки ~`28-45`

- `tools/processforge.py`
  - `PROCESS_CATALOG_CLASSIFICATIONS` — строки ~`14036-14040`
  - `process_catalog_metadata(...)` — строки ~`14045-14063`

### 2) Вызовы и потребители

- `src/processforge_core/process_catalog/service.py`
  - `process_catalog_metadata` вызывается из:
    - `process_catalog_role(...)` (`src/processforge_core/process_catalog/service.py:52-55`)
  - Здесь `PROCESS_CATALOG_CLASSIFICATIONS` используется только внутри `process_catalog_metadata` для нормализации/валидации значения `classification`.

- `tools/processforge.py`
  - `process_catalog_metadata` определяется локально и вызывается из:
    - `process_is_public_stable(...)` (`~14064-14066`)
    - `process_catalog_doctor(...)` (`~14113-14121`, включая явную проверку `meta["classification"] in PROCESS_CATALOG_CLASSIFICATIONS` `~14119`)
    - `builtin_process_catalog_report(...)` (`~14284-14286` и далее формирование отчёта)
  - `PROCESS_CATALOG_CLASSIFICATIONS` используется:
    - в `process_catalog_metadata(...)` для нормализации (`~14049`)
    - в валидации доктора (`~14119`)
  - Импортный мост с ядра:
    - `from processforge_core.process_catalog import (...) as catalog_*` (`~45-52`) и `process_catalog_core` (`~54`)
    - обёртки:
      - `process_catalog_role(...)` в `tools/processforge.py` делегирует в `catalog_process_catalog_role` (`~12472-12474`)
      - `process_catalog_entries(...)`, `resolve_process_definition(...)`, `require_official_process_active(...)`, `process_definition_exists(...)` делегируют в ядро (`~12583-12619`)

### 3) Разделение по типу потребителей

- `catalog/resolve` (ядро/поведенческая логика разрешения)
  - `process_catalog_service`: `process_catalog_entries`, `resolve_process_definition`, `require_official_process_active`, `process_catalog_role`
  - В этой области `classification` используется только косвенно через `process_catalog_role` → `process_catalog_metadata`.

- `validation/reporting` (CLI‑доктор/отчёты)
  - `tools/processforge.py`: `process_is_public_stable`, `process_catalog_doctor` (строки ~`14113+`), `builtin_process_catalog_report` (`~14265+`).
  - Здесь локально дублированный `process_catalog_metadata` + `PROCESS_CATALOG_CLASSIFICATIONS` дублируют ядро.

### 4) Минимальная граница для Phase D (preserve behavior)

- Вынести поведение классификации в один источник в `processforge_core.process_catalog`:
  - оставить `PROCESS_CATALOG_CLASSIFICATIONS` и `process_catalog_metadata` только в `service.py`
- В `tools/processforge.py` заменить локальные дубли на импорт из `processforge_core.process_catalog.service`:
  - убрать локальные `PROCESS_CATALOG_CLASSIFICATIONS` и локальный `process_catalog_metadata`
  - использовать уже существующие ядровые API (через импорт или обёртки)
- Для поведения без изменений оставить фасадные публичные функции в `tools/processforge.py`, если на них завязаны внешние вызовы/тесты:
  - сохранить интерфейс `process_catalog_role/process_catalog_entries/resolve_process_definition/...` как сейчас, меняя только внутреннюю реализацию на ядро
- Ограничение: текущая инвентаризация выполнена только по разрешённым файлам, поэтому callsites вне этих файлов не проверялись.