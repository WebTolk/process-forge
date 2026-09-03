# Review: Phase B bootstrap package/import seam

## Verdict

**Статус: `pass_with_conditions`**

Идея Phase B в целом верная: вынос bootstrap seam в `src/processforge_core/bootstrap.py` и сохранение `tools/processforge.py` как единственного legacy core/CLI entrypoint соответствует текущему коду. Но в спецификации не хватает одного критического уточнения:

**при сохранении direct-script запуска `tools/pf_runtime/mcp_server.py` и `tools/pf_runtime/codex_hooks.py` полностью убрать локальный path-based bootstrap нельзя.**
Минимальный локальный shim в этих двух файлах всё равно нужен, иначе `src/processforge_core/bootstrap.py` физически недостижим до появления `src` на import path.

## Что подтверждено по коду

1. `bin/pf.py` не участвует в проблеме bootstrap seam.
   Он только вычисляет root и запускает `tools/processforge.py` как отдельный процесс: `bin/pf.py:27-33`.

2. Оба direct-script adapter сейчас живут за счёт локального `sys.path` hack.
   - `tools/pf_runtime/mcp_server.py:13-15` добавляет `tools` в `sys.path`, затем делает `importlib.import_module("processforge")` (`:26-27`) и `from pf_runtime import host` (`:31`).
   - `tools/pf_runtime/codex_hooks.py:19-21` делает то же самое, затем `importlib.import_module("processforge")` (`:31-32`) и `from pf_runtime import host, service` (`:72`).

3. `host.py` и `service.py` нельзя безопасно грузить как произвольные file modules.
   Они являются package modules и зависят от relative imports:
   - `tools/pf_runtime/host.py:20` -> `from . import RUNTIME_PROTOCOL_VERSION`
   - `tools/pf_runtime/service.py:27-28` -> `from . import RUNTIME_PROTOCOL_VERSION`, `from . import host`

4. `tools/processforge.py` тоже требует доступности `tools` как import root.
   У него top-level импорт `processforge_subprocess`: `tools/processforge.py:32`.
   Значит bootstrap обязан обеспечить importability `tools` **до** выполнения legacy core модуля.

5. Спецификация права в том, что нужно возвращать именно legacy module object, а не facade.
   Runtime-команды в `tools/processforge.py` передают `sys.modules[__name__]` в `host/service`: `tools/processforge.py:18385-18507`.
   Это подтверждает, что `bootstrap` должен отдавать реальный module object `tools/processforge.py`.

## Главная поправка к спецификации

### Что невозможно
Если оставить текущий контракт запуска:
- `python tools/pf_runtime/mcp_server.py`
- `python tools/pf_runtime/codex_hooks.py`

то **нулевой** локальный bootstrap в этих файлах невозможен.
Причина простая: при direct-script запуске Python ещё не знает ни про `src`, ни про `tools` как package roots.

### Что возможно и корректно
Нужен **минимальный** local shim только для загрузки `bootstrap.py`, а вся остальная логика должна переехать в `src/processforge_core/bootstrap.py`.

Это и есть правильная граница для Phase B:
- убрать дублированные `sys.path.insert(...TOOLS_ROOT...)`
- убрать дублированные `import_module("processforge")`
- оставить только маленький path-based loader bootstrap-модуля

## Рекомендуемая исправленная схема

### 1. В `mcp_server.py` и `codex_hooks.py`
Оставить только минимальный shim вида:
- вычислить `repo_root` от `__file__`
- найти `repo_root / "src" / "processforge_core" / "bootstrap.py"`
- загрузить этот файл через `importlib.util.spec_from_file_location(...)`
- вызвать `bootstrap_runtime(__file__)`

Если цель именно **полностью** убрать и этот shim, тогда надо менять launch contract:
- запускать adapters не direct-script способом, а через wrapper/module mode
  например через `tools/processforge.py` или `python -m ...`

Но это уже больше Phase C / launcher refactor, а не текущий behavior-preserving Phase B.

### 2. В `src/processforge_core/bootstrap.py`
`bootstrap.py` должен быть self-contained и stdlib-only, без зависимости на то, что `src` уже импортируем.

Рекомендуемое поведение:

1. Вычислить `repo_root` из `caller_file`.
2. Централизованно добавить `repo_root / "tools"` в `sys.path`, если его там нет.
3. При необходимости добавить `repo_root / "src"` в `sys.path` после старта bootstrap.
4. Загрузить `tools/processforge.py` через `spec_from_file_location(...)` под **одним каноническим ключом**.
5. Переиспользовать уже загруженный module object из `sys.modules`, если он есть.
6. Для защиты от второго legacy core модуля:
   - либо дополнительно связать `sys.modules["processforge"]` с тем же object,
   - либо ввести и проверить инвариант, что name-based import `processforge` больше нигде не используется.
7. Импортировать `pf_runtime.host` и `pf_runtime.service` только через обычный package import:
   - `importlib.import_module("pf_runtime.host")`
   - `importlib.import_module("pf_runtime.service")`

### 3. Что не надо делать
- Не загружать `host.py`/`service.py` через file-location import.
- Не строить новый facade над legacy core.
- Не менять `bin/pf.py`.
- Не менять Windows detached-runtime flow в `service.py:519-527`.

## Риск второй копии legacy core

По проверенным файлам второй module object сейчас создаётся только из-за текущих adapter imports по имени `processforge`. После перевода adapters на bootstrap этот риск почти исчезает.

Но спецификация в текущем виде всё ещё недосказывает важное:
- если `tools/processforge.py` загрузить только под private/internal key,
- и где-то ещё останется `import processforge`,

то Python создаст **второй** модуль из того же файла.

Поэтому для надёжного Phase B рекомендую одно из двух:
- **предпочтительно:** после загрузки legacy core привязать `sys.modules["processforge"]` к тому же object;
- **минимально допустимо:** явно зафиксировать как gate, что в кодовой базе больше нет `import processforge` / `import_module("processforge")` вне bootstrap.

По доступной области чтения name-based import остался только в:
- `tools/pf_runtime/mcp_server.py`
- `tools/pf_runtime/codex_hooks.py`

## Итоговая рекомендация

Спецификацию стоит принять **с одной обязательной правкой формулировки**:

> `src/processforge_core/bootstrap.py` может централизовать весь runtime/core bootstrap, но direct-script adapters всё равно должны сохранить минимальный локальный shim для первичной загрузки самого `bootstrap.py`, если не меняется контракт запуска. Внутри `bootstrap.py` нужно централизованно делать `tools` importable, грузить legacy core один раз, импортировать `pf_runtime.host/service` как package modules и предотвращать вторую загрузку legacy core по имени `processforge`.

Это делает Phase B:
- достижимым на Windows,
- совместимым с current direct-script entrypoints,
- корректным для package imports,
- и безопасным по module identity.