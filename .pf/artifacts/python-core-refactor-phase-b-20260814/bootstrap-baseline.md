# Bootstrap baseline (python-core-phase-b-bootstrap-baseline)

## 1) Каркас direct-script bootstrap/import

1. `bin/pf.py` — lightweight launcher (Windows-aware):
- `ROOT = Path(__file__).resolve().parents[1]`
- `cli = root / "tools" / "processforge.py"`
- `exec_processforge()`:
  - на Windows: `os.spawnv(os.P_WAIT, sys.executable, [sys.executable, cli, *argv])`
  - иначе: `os.execv(...)`
- Это внешний вход в `tools/processforge.py` без загрузки Core как модуля.

2. `tools/processforge.py` — главный CLI-скрипт:
- Импортов `sys.path`-хаков в начале нет; это прямой скрипт в каталоге distribution.
- Основной вход:
  - `if __name__ == "__main__": sys.exit(main())`
- `main(argv)` делает разбор аргументов через `build_parser()`, затем вызывает `args.func(args)`.
- Логика в `exec_processforge(...)` выше (из `bin/pf.py`) не меняет runtime state до выполнения выбранной команды.

3. MCP-контур: `tools/pf_runtime/mcp_server.py`
- `TOOLS_ROOT = Path(__file__).resolve().parents[1]`
- `sys.path.insert(0, TOOLS_ROOT)` (если отсутствует)
- `core_module()` ⇒ `importlib.import_module("processforge")`
- В `main()` после парсинга аргументов сразу `core = core_module()`, затем `core.resolve_workplace_root(...)`.
- В `respond()` для tool-calls используется `from pf_runtime import host` (отложенно в функции).

4. Hook-контур: `tools/pf_runtime/codex_hooks.py`
- Аналогичная bootstrap-механика:
  - `TOOLS_ROOT` + `sys.path.insert(0, TOOLS_ROOT)`
  - `core_module()` ⇒ `importlib.import_module("processforge")`
- `dispatch()`:
  - после нормализации события делает `from pf_runtime import host, service` внутри функции.
  - пытается доставку через `service.runtime_request(...)` (если неуспех — fallback в `host.ingest_event(...)`).
- `main()` читает JSON со `stdin`, возвращает `0` даже при ошибках (в debug-режиме печатает JSON-статус).

## 2) Безопасные non-mutating checks (без конфигурированного workplace)

| Команда | Exit code | Наблюдаемое поведение |
|---|---:|---|
| `python bin/pf.py --help` | `0` | Печать help для полного CLI-повторения `tools/processforge.py` (список команд, флаги). |
| `python tools/processforge.py --help` | `0` | Печать help того же CLI; без доступа к проекту/распаковке. |
| `python tools/pf_runtime/mcp_server.py --workplace . --help` | `0` | Печать usage MCP-скрипта (требуется `--workplace`). |
| `"{\"jsonrpc\":\"2.0\",\"id\":1,\"method\":\"initialize\"}\n{\"jsonrpc\":\"2.0\",\"id\":2,\"method\":\"tools/list\"}" \| python tools/pf_runtime/mcp_server.py --workplace .` | `0` | Возврат MCP-ответов `initialize` и `tools/list` с `version=1.0.2`. |
| `{"hook_event_name":"SessionStart","source":"startup","cwd":"C:/Windows","session_id":"test-session","turn_id":"t1","tool_name":"Bash","tool_use_id":"u1"}` with `PF_CODEX_HOOK_DEBUG=1` \| `python tools/pf_runtime/codex_hooks.py` | `0` | Вывод `{\"status\": \"ignored\", \"reason\": \"not_processforge_project\"}` — безопасный игнор для не PF-проекта. |
| `python -c "import importlib; import tools.pf_runtime.mcp_server as m; import tools.pf_runtime.codex_hooks as h; import tools.processforge as p; print('ok', m.__name__, h.__name__, p.__name__)"` | `0` | Импорт модулей выполняется; модульная загрузка без запуска runtime loop. |

## 3) Наблюдение по состоянию и рискам baseline

- Текущий bootstrap на MCP/hook уровне опирается на прямой импорт `processforge` через `importlib`, при этом дополнительно вставляется `TOOLS_ROOT` для поиска legacy-модуля.
- В hook-контуре есть `fallback` в `host` при недоступности runtime, но путь доставки события всё равно остаётся через PF runtime API в активной ветке.
- По текущему `--help` поведению и stdin-тестам видно, что запусковые скрипты остаются "import-first + parser-first" и не требуют предварительно настроенного workplace для получения справки; однако runtime-событийная логика зависит от контекста проекта в момент dispatch.
