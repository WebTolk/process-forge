# package-bootstrap-implementation

## Статус
`blocked`

Реализация Phase B в этом запуске не выполнена. Текущий worker не может безопасно доставить требуемый результат по двум независимым причинам:

1. Среда запущена в `read-only` режиме без возможности эскалации, поэтому нельзя создать/изменить:
   - `src/processforge_core/__init__.py`
   - `src/processforge_core/bootstrap.py`
   - `tools/pf_runtime/mcp_server.py`
   - `tools/pf_runtime/codex_hooks.py`
   - `tools/smoke_processforge_core_package_bootstrap.py`

2. В капсуле уже зафиксирован `overlap_check: fail` для записи в `tools/**`:
   - `tools/pf_runtime/mcp_server.py` конфликтует с assignment `pre-release-remediation-implementation-20260730`
   - `tools/pf_runtime/codex_hooks.py` конфликтует с assignment `pre-release-remediation-implementation-20260730`
   - `tools/smoke_processforge_core_package_bootstrap.py` конфликтует с `tools/smoke_*.py` и `tools/**` того же assignment

По политике `block_on_write_overlap` такой scope нельзя править до разведения ownership.

## Подтверждённый baseline
Текущие runtime adapters действительно используют локальный bootstrap, который и должен быть заменён в Phase B:

- `tools/pf_runtime/mcp_server.py`
  - добавляет `TOOLS_ROOT` в `sys.path`
  - загружает legacy core через `importlib.import_module("processforge")`
  - затем импортирует `pf_runtime.host`

- `tools/pf_runtime/codex_hooks.py`
  - использует тот же `TOOLS_ROOT` + `sys.path.insert(...)`
  - загружает `processforge` через `importlib.import_module("processforge")`
  - затем импортирует `pf_runtime.host` и `pf_runtime.service`

Это соответствует spec/review: текущая точка шва существует, но ещё не вынесена в `src/processforge_core/bootstrap.py` и не переведена на минимальный first-load shim + `bootstrap_runtime(__file__)`.

## Выполненные проверки
Проверены только безопасные non-mutating baseline-команды:

- `python bin/pf.py --help` -> `exit 0`
- `python tools/processforge.py --help` -> `exit 0`
- `python tools/pf_runtime/mcp_server.py --workplace . --help` -> `exit 0`
- `initialize` + `tools/list` через `tools/pf_runtime/mcp_server.py --workplace .` -> `exit 0`
  - сервер отвечает `protocolVersion: 2024-11-05`
  - публикует 4 инструмента: `pf.project_state`, `pf.work_state`, `pf.resolve`, `pf.workplace_state`
- `PF_CODEX_HOOK_DEBUG=1` + `python tools/pf_runtime/codex_hooks.py` вне PF-проекта -> `exit 0`
  - ответ: `{"status": "ignored", "reason": "not_processforge_project"}`

Не выполнено:
- собственно Phase B implementation
- smoke для нового `processforge_core`
- post-change characterization
- release/archive smoke после изменения

## Что должно быть сделано после разблокировки
1. Создать `src/processforge_core/__init__.py`.
2. Создать stdlib-only `src/processforge_core/bootstrap.py`.
3. Заменить дублированный bootstrap в `tools/pf_runtime/mcp_server.py` на минимальный shim, который file-location загрузит `bootstrap.py`, затем вызовет `bootstrap_runtime(__file__)`.
4. Аналогично заменить bootstrap в `tools/pf_runtime/codex_hooks.py`.
5. Обеспечить:
   - импортируемость `tools`
   - ровно один reused module object для legacy `tools/processforge.py`
   - защиту identity модуля `processforge`
   - загрузку `pf_runtime.host` и `pf_runtime.service` как обычных package modules
6. Добавить `tools/smoke_processforge_core_package_bootstrap.py`.
7. Повторно прогнать characterization checks из spec.

## Вывод
Scope для анализа был достаточен, но scope для доставки реализации в текущем запуске недостаточен. Для продолжения нужен новый worker-run с записью и без ownership-конфликта на `tools/**`, либо явное перераспределение write-scope между assignment’ами.