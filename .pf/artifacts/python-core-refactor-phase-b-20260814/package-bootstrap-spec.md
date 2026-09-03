# Phase B: спецификация bootstrap package/import seam

## Цель
Зафиксировать минимальный Phase B, который убирает неявный import bootstrap из runtime/MCP adapters, но не переносит process semantics из `tools/processforge.py`. Phase B остаётся строго `behavior-preserving` и подготавливает только Phase C.

## Наблюдаемое текущее состояние
- `bin/pf.py` не импортирует Core; он только вычисляет root и spawn/exec запускает `tools/processforge.py`.
- `tools/processforge.py` остаётся живым монолитом и текущим источником поведения; runtime wrappers внутри него импортируют `pf_runtime.service` / `pf_runtime.host` и передают `sys.modules[__name__]` как `core`.
- `tools/pf_runtime/mcp_server.py` и `tools/pf_runtime/codex_hooks.py` сейчас держатся на рассыпанном bootstrap: `sys.path.insert(0, TOOLS_ROOT)` плюс `importlib.import_module("processforge")`.
- `tools/pf_runtime/host.py` и `tools/pf_runtime/service.py` уже работают как package modules и ожидают переданный `core`; они не являются каноническими direct-script entrypoints.
- Блок `tools/processforge.py:3730-3859` выглядит как второй launcher, но это встроенный template string, не живой top-level код.

## Решение для Phase B
Создать только явный package shell и один общий bootstrap seam:

```text
src/processforge_core/
  __init__.py
  bootstrap.py
```

Никакие process/runtime/worker semantics в этом Phase B не переносятся. `tools/processforge.py` остаётся каноническим legacy core module и CLI script.

## Один bootstrap seam
Публичный контракт Phase B:

```python
@dataclass(frozen=True)
class RuntimeBootstrap:
    repo_root: Path
    core: ModuleType
    host: ModuleType
    service: ModuleType

def bootstrap_runtime(caller_file: str | Path) -> RuntimeBootstrap: ...
```

Требования к `bootstrap_runtime(...)`:
- Вычисляет `repo_root` от `caller_file`.
- Загружает `tools/processforge.py` как legacy core module один раз под стабильным internal module key.
- Загружает runtime modules `pf_runtime.host` и `pf_runtime.service` централизованно, чтобы adapters больше не делали собственный `sys.path.insert(...)`.
- Кэширует результат в `sys.modules`.
- Не создаёт новый facade с копированием методов. Возвращаемый `core` — это тот же legacy module object, чтобы не получить второй скрытый API.

После этого:
- `tools/pf_runtime/mcp_server.py` получает `core` и `host` только через `bootstrap_runtime(__file__)`.
- `tools/pf_runtime/codex_hooks.py` получает `core`, `host`, `service` только через `bootstrap_runtime(__file__)`.
- Прямые `sys.path.insert(...)` и `importlib.import_module("processforge")` из этих двух adapters удаляются.

## Точный Core contract, который Phase B обязан сохранить
`bootstrap.py` не сужает и не переименовывает текущий module surface, который уже нужен runtime слоям.

`service.py` использует:
- `ROOT`
- `check`
- `dump_yaml`
- `event_runtime_paths`
- `json_read`
- `locate_flow_root`
- `now_utc`
- `print_checks`
- `process_pid_running`
- `project_id`
- `resolve_workplace_root`
- `update_stale_agent_presence`
- `workplace_agent_ledger_path`

`host.py` использует:
- `append_process_event`
- `check`
- `command_agent_checkin`
- `command_agent_checkout`
- `command_agent_director_tick`
- `command_agent_heartbeat`
- `command_supervisor_tick`
- `dump_yaml`
- `effective_project_coordination`
- `event_id_value`
- `event_runtime_paths`
- `find_agent_presence`
- `flow_label`
- `iter_agent_presence`
- `json_read`
- `load_agent_run_state`
- `load_task`
- `load_yaml_document`
- `locate_flow_root`
- `normalize_required_outputs`
- `now_utc`
- `print_checks`
- `processforge_event`
- `project_context_check_result`
- `project_context_snapshot_paths`
- `project_id`
- `read_current_project_session`
- `rel`
- `require_flow_root`
- `resolve_process_definition`
- `resolve_workplace_root`
- `safe_id`
- `supervisor_state_path`
- `task_output_path`
- `task_process_id`
- `task_verification_fingerprint`
- `update_stale_agent_presence`

`mcp_server.py` дополнительно опирается на:
- `project_id`
- `resolve_workplace_root`

`codex_hooks.py` дополнительно опирается на:
- `require_flow_root`
- `resolve_workplace_root`

Phase B не меняет этот contract. Phase C уже сможет выделять меньшие typed APIs.

## Изменяемые файлы и ownership
Обязательные Phase B изменения:
- `src/processforge_core/__init__.py`
- `src/processforge_core/bootstrap.py`
- `tools/pf_runtime/mcp_server.py`
- `tools/pf_runtime/codex_hooks.py`

По умолчанию не менять в Phase B:
- `bin/pf.py`
- `tools/processforge.py`
- `tools/pf_runtime/host.py`
- `tools/pf_runtime/service.py`

Исключение только одно: если characterization покажет реальный import/startup break, допускается узкий фикс в `bin/pf.py` или `tools/processforge.py`, но без переноса domain logic.

Из-за активного legacy assignment с ownership на `tools/**` Phase B implementation требует отдельный handoff/разрешение на запись в `tools/pf_runtime/*.py`. Этот отчёт ничего в `tools/**` не меняет.

## Characterization checks
Минимальный gate до и после переключения bootstrap:
1. `python bin/pf.py --help` работает без изменения текста ошибок/exit semantics.
2. `python tools/processforge.py --help` работает.
3. `python tools/pf_runtime/mcp_server.py --workplace <workplace>` принимает `initialize` и `tools/list`, не падает на import startup.
4. `python tools/pf_runtime/codex_hooks.py` на payload вне PF project завершаетcя `0` и не превращает hook в failure point.
5. `python bin/pf.py runtime status --workplace <workplace>` работает.
6. `python bin/pf.py runtime start|status|stop --workplace <workplace>` сохраняет текущую Windows detached-subprocess модель.
7. Release/archive smoke: в архив попадают `src/processforge_core/__init__.py` и `src/processforge_core/bootstrap.py`, launcher paths не теряются.

## Windows и direct-script considerations
- `bin/pf.py` должен остаться spawn/exec launcher; перевод на in-process import в Phase B запрещён.
- `service.py` сейчас стартует runtime через `sys.executable` + `core.ROOT / "tools" / "processforge.py"`; этот путь Phase B не меняет.
- `host.py` и `service.py` не нужно делать standalone direct scripts. Канонический путь остаётся через `tools/processforge.py runtime ...`.
- Bootstrap обязан работать из direct-script callers `tools/pf_runtime/mcp_server.py` и `tools/pf_runtime/codex_hooks.py` без file-local `sys.path.insert(...)`.
- Проверки нужно гонять на Windows path handling, subprocess launch и путях с реальным workplace root.

## Строгие non-goals
- Не переносить `resolve_process_definition`, normalization, validation, doctor logic в Core.
- Не менять `host.py::ingest_event`, projections, work-state, runtime transport, worker lifecycle.
- Не вводить compatibility aliases внутрь `processforge_core`, кроме самого bootstrap seam.
- Не переписывать `bin/pf.py` в импортный launcher.
- Не делать `host.py`/`service.py` новыми public entrypoints.
- Не чистить legacy duplicates и compatibility branches в этом Phase B.

## Последовательность внедрения
1. Создать `src/processforge_core/__init__.py` и `bootstrap.py`.
2. Перевести `mcp_server.py` на `bootstrap_runtime(__file__)`.
3. Перевести `codex_hooks.py` на `bootstrap_runtime(__file__)`.
4. Прогнать characterization и Windows/release smoke.
5. Только при подтверждённом break внести узкий launcher fix; иначе `bin/pf.py`, `tools/processforge.py`, `host.py`, `service.py` оставить без изменений.

## Критерий готовности Phase B
Phase B считается завершённым, если import/bootstrap seam централизован в одном модуле, adapters больше не содержат `sys.path.insert(...)` и `importlib.import_module("processforge")`, а всё остальное поведение по-прежнему идёт из legacy `tools/processforge.py` без domain extraction.