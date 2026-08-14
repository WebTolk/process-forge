# package-bootstrap-implementation-retry

## Статус
`blocked`

## Подтверждённое текущее состояние
- Phase B в репозитории не внедрён.
- Файлы `src/processforge_core/__init__.py`, `src/processforge_core/bootstrap.py` и `tools/smoke_processforge_core_package_bootstrap.py` отсутствуют.
- `tools/pf_runtime/mcp_server.py` всё ещё использует локальный bootstrap через `TOOLS_ROOT` + `sys.path.insert(...)` (`13-15`), затем `importlib.import_module("processforge")` (`26-27`) и обычный `from pf_runtime import host` (`31`).
- `tools/pf_runtime/codex_hooks.py` остаётся на том же path-based bootstrap: `TOOLS_ROOT` + `sys.path.insert(...)` (`19-21`), `importlib.import_module("processforge")` (`31-32`), `from pf_runtime import host, service` (`72`).
- `tools/processforge.py` по-прежнему является legacy core/CLI entrypoint с `ROOT = Path(__file__).resolve().parents[1]` (`35`) и передачей `sys.modules[__name__]` в runtime host/service (`18387-18507`).
- `bin/pf.py` остаётся тонким launcher’ом, который запускает `tools/processforge.py` через `os.spawnv`/`os.execv` (`18-28`).

## Невыполненная часть assignment
Из-за отсутствия прав записи не удалось:
- создать `src/processforge_core/__init__.py`;
- создать stdlib-only `src/processforge_core/bootstrap.py`;
- заменить bootstrap в `tools/pf_runtime/mcp_server.py`;
- заменить bootstrap в `tools/pf_runtime/codex_hooks.py`;
- добавить `tools/smoke_processforge_core_package_bootstrap.py`;
- выполнить post-change characterization и smoke уже по новой схеме.

## Проверки baseline
Успешно подтверждено текущее поведение без изменений кода:
- `python bin/pf.py --help` -> `exit 0`
- `python tools/processforge.py --help` -> `exit 0`
- `python tools/pf_runtime/mcp_server.py --workplace . --help` -> `exit 0`
- `initialize` + `tools/list` через `tools/pf_runtime/mcp_server.py --workplace .` -> `exit 0`, `protocolVersion=2024-11-05`, инструменты: `pf.project_state`, `pf.work_state`, `pf.resolve`, `pf.workplace_state`
- `PF_CODEX_HOOK_DEBUG=1` + `python tools/pf_runtime/codex_hooks.py` вне PF-проекта -> `exit 0`, ответ `{"status": "ignored", "reason": "not_processforge_project"}`

## Блокер
Текущий worker-run запущен в окружении с файловой политикой `read-only`. Assignment разрешает изменять код, но фактическая среда выполнения не позволяет создать или изменить требуемые файлы, поэтому implementation retry завершить в этом запуске невозможно.

## Что нужно для следующего запуска
1. Дать этому assignment writable execution environment.
2. Сохранить текущий scope файлов без расширения.
3. После открытия записи внедрить Phase B seam ровно по spec/review:
   - path-based first-load shim в обоих adapters;
   - `bootstrap_runtime(__file__)`;
   - единый legacy module object для `tools/processforge.py`;
   - обычный package import для `pf_runtime.host` и `pf_runtime.service`;
   - отдельный smoke для `processforge_core` bootstrap.