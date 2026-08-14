# postchange-characterization

## Результаты non-mutating checks (`python-core-phase-b-postchange-characterization`)

1) **Package bootstrap smoke**
- Команда: `python tools/smoke_processforge_core_package_bootstrap.py`
- Код выхода: `0`
- Утверждение: bootstrap-цепочка загрузилась успешно (ядро, host, service), MCP/hook-рантаймные bootstrap-адаптеры и критические инварианты корректны; скрипт завершился `ok`.

2) **CLI launcher help через `bin/pf.py`**
- Команда: `python bin/pf.py --help`
- Код выхода: `0`
- Утверждение: `bin/pf.py` корректно исполняет оболочку над `tools/processforge.py` и отдаёт полноценный `--help` процесс-фреймворка.

3) **CLI core help через `tools/processforge.py`**
- Команда: `python tools/processforge.py --help`
- Код выхода: `0`
- Утверждение: CLI поднимается, парсер строится и выводит перечень команд (инициализация/doctor/runtime/worker и др.) без ошибок.

4) **MCP initialize + tools/list через Python-подпроцесс (без BOM)**
- Команда:
  - `@'... ' @ | python -`
  (`subprocess.Popen([sys.executable, 'tools/pf_runtime/mcp_server.py', '--workplace', '.'], ...), payload = initialize+tools/list`)
- Код выхода: `0`
- Утверждение: сервер обработал оба JSON-RPC запроса; `initialize` вернул `protocolVersion:"2024-11-05"` и `serverInfo.version:"1.0.2"`, `tools/list` вернул 4 инструмента (`pf.project_state`, `pf.work_state`, `pf.resolve`, `pf.workplace_state`).

5) **Hook-игнор вне PF-проекта**
- Команда:
  - `@'... '@ | python -`
  (`PF_CODEX_HOOK_DEBUG=1`, payload `SessionStart` с `cwd:"C:/Windows"`)
- Код выхода: `0`
- Утверждение: возвращён JSON-результат `{"status":"ignored","reason":"not_processforge_project"}`.

6) **Runtime status (только чтение состояния)**
- Команда: `python tools/processforge.py runtime status --json --workplace .`
- Код выхода: `0`
- Утверждение: состояние прочитано без запуска/остановки runtime; статус сервиса сейчас `stale` (не меняется действиями проверки), процесс и runtime-метрики доступны в JSON-ответе.