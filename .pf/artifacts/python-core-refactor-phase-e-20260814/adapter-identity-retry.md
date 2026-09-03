# adapter-identity-retry

## Результат проверки (assurance, без правок)

- `ProcessCatalog` доступен в CLI только через package-level API `processforge_core.process_catalog`, без прямого импорта `processforge_core.process_catalog.service`.

## Использованные команды

1. `Get-Content -Path tools/processforge.py`
2. `Get-Content -Path src/processforge_core/process_catalog/__init__.py`
3. `Get-Content -Path src/processforge_core/process_catalog/service.py`
4. `rg -n "processforge_core\.process_catalog\.service|from processforge_core\.process_catalog|import .*service" tools/processforge.py src/processforge_core/process_catalog/__init__.py src/processforge_core/process_catalog/service.py`
5. `rg -n "def _official_process_definition_refs|def process_root_candidates|def _process_root_candidates|def process_root_yaml_files|def _process_root_yaml_files" src/processforge_core/process_catalog/service.py`

## Выводы по задачной цели

1. **Идентичность адаптера импортов подтверждена**
   - В `tools/processforge.py` импорт идёт как:
     - `from processforge_core.process_catalog import (official_process_definition_refs as catalog_official_process_definition_refs, process_root_candidates as catalog_process_root_candidates, process_root_yaml_files as catalog_process_root_yaml_files, ...)`
   - В `src/processforge_core/process_catalog/__init__.py` эти имена реэкспортируются из `process_catalog.service`.
   - Таким образом, runtime-идентичность для CLI идёт через package-level модуль, а не через прямой импорт внутреннего service-модуля.

2. **Точно проверены целевые функции**
   - `_official_process_definition_refs` и обёртка `official_process_definition_refs` присутствуют в `service.py`.
   - `_process_root_candidates` и `process_root_candidates` присутствуют в `service.py`.
   - `_process_root_yaml_files` и `process_root_yaml_files` присутствуют в `service.py`.

3. **Контроль на прямой импорт service-модуля**
   - По grep-поиску по трем разрешённым файлам прямых импортов вида `from processforge_core.process_catalog.service ...` нет.
   - Единственные совпадения `service` в `tools/processforge.py` относятся к `pf_runtime` (`from pf_runtime import service as runtime_service`) и не относятся к `process_catalog`.

## Заключение

Гэп по Characterization Phase E закрыт для запрошенного участка: пакетная прослойка сохранена, целевые переменные идентичности присутствуют и разрешаются через `processforge_core.process_catalog`, прямой импорт service-модуля процесса каталога отсутствует.