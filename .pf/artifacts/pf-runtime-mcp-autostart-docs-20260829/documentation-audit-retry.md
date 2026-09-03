# Аудит документации Runtime/MCP

Задача: инвентаризация заявлений документации Runtime/MCP, фактического поведения исполняемого lifecycle, противоречий и требований Windows autostart по разрешённым файлам.

## Проверенные источники

Документация:
- `docs/concepts/runtime-mcp.md`
- `docs/ru/concepts/runtime-mcp.md`
- `docs/concepts/runtime-model.md`
- `docs/ru/concepts/runtime-model.md`
- `docs/concepts/codex-session-read.md`
- `docs/concepts/hooks-events.md`
- `docs/ru/concepts/hooks-events.md`
- `docs/known-limitations.md`
- `docs/ru/known-limitations.md`
- `docs/getting-started/installation.md`
- `docs/index.md`
- `docs/ru/index.md`

Код:
- `tools/pf_runtime/service.py`
- `tools/pf_runtime/mcp_server.py`
- `tools/pf_runtime/codex_integration.py`
- `tools/processforge.py`
- `bin/pf.py`

## Фактическая модель Runtime по коду

`tools/pf_runtime/service.py` реализует долгоживущий локальный Runtime process:

- CLI lifecycle: `runtime serve`, `runtime start`, `runtime stop`, `runtime restart`, `runtime status`, `runtime doctor`.
- Background start есть: `runtime start` запускает отдельный процесс через `subprocess.Popen`.
- На Windows используется `CREATE_NEW_PROCESS_GROUP | DETACHED_PROCESS`.
- IPC: loopback HTTP на `127.0.0.1`, endpoint пишется в workplace runtime state.
- Auth: bearer token хранится в workplace runtime path, в state публикуется `token_hash`.
- Singleton: lock/state/PID проверяются через `runtime.lock`, `service.json`, PID readiness и `/readyz`.
- Scheduler loop есть: периодически запускает Ledger maintenance, Director, Inspector, projection tick через Runtime Host helpers.
- Runtime state расположен в workplace: `<workplace>/runtime/pf-runtime/`.

Это означает, что формулировка “нет daemon/background process” верна только для базового file-first core/default usage, но уже не полна для optional PF Runtime lifecycle.

## Фактическая модель MCP по коду

`tools/pf_runtime/mcp_server.py` реализует stdio MCP facade, но он не полностью read-only:

- Read tools: `pf.context`, `pf.project_state`, `pf.project_initialization.status`, `pf.work_state`, `pf.resolve`, `pf.search`, `pf.workplace_state`, `pf.session_context`, `pf.session_chat`, `pf.session_activity`.
- Mutating tools объявлены отдельно: `pf.project_initialization.initialize`, `pf.project_initialization.repair`, `pf.work.start`.
- `pf.project_initialization.initialize` и `pf.project_initialization.repair` требуют `apply: true`.
- `pf.work.start` создаёт или продолжает governed work через `GovernedWorkBootstrapService.start(...)`.
- Garage tools могут работать от `project_root`; session-scoped tools требуют Ledger session.
- `PF_MCP_SESSION_ID` поддерживается как default session id, но mismatch с tool argument отклоняется `session_mismatch`.

Следовательно, документация, где MCP называется “read-only” без уточнения исключений, устарела или противоречит текущему коду.

## Основные противоречия

1. `docs/ru/concepts/runtime-mcp.md` сильно устарел относительно английского документа и кода:
   - заявляет только `pf.project_state`, `pf.work_state`, `pf.resolve`, `pf.workplace_state`;
   - не содержит `pf.context`, `pf.project_initialization.*`, `pf.work.start`, `pf.search`, `pf.session_*`;
   - утверждает, что сервер требует session identity, хотя английский документ и код допускают Garage reads с `project_root`.

2. `docs/concepts/runtime-model.md` содержит две модели в одном файле:
   - первая часть говорит, что optional Runtime/MCP являются адаптерами вокруг Core и core runtime не требует daemon;
   - вторая часть описывает PF Runtime как workplace-scoped host, scheduler и IPC transport.
   Это не фатальное противоречие, но нужна явная граница: “core/default CLI не daemon; optional `runtime start` запускает background service”.

3. `docs/known-limitations.md` говорит:
   - “There is no daemon or watch-events service.”
   - ниже: “A bounded file-first supervisor MVP exists. A background daemon ... not implemented.”
   При этом `tools/pf_runtime/service.py` уже содержит long-lived Runtime process и background start. Корректнее: “нет обязательного daemon/watch-events service; optional PF Runtime PoC/MVP существует”.

4. `docs/getting-started/installation.md` говорит “ProcessForge v0.1 does not require a daemon or background process.”
   Текущие версии в коде: `PROCESSFORGE_VERSION = 1.1.0`, `RUNTIME_VERSION = 1.0.0-poc`. Упоминание `v0.1` выглядит устаревшим.

5. `docs/concepts/codex-session-read.md` утверждает, что `UserPromptSubmit`, `Stop`, `SubagentStop` пишут transcript, а `SessionStart` supplies Ledger id to the turn. Это согласуется с заявленной моделью, но в `docs/ru/concepts/hooks-events.md` всё ещё сказано, что общий захват assistant/subagent responses пока не реализован. Нужно синхронизировать RU/EN: generic responses не гарантированы, но `Stop.last_assistant_message` и `SubagentStop` поддерживаются, если Codex предоставляет эти поля.

## Windows autostart: что есть и чего нет

В разрешённых файлах найдено:

- Windows detached background launch в `runtime start`.
- Project-local hook installer пишет `.codex/hooks.json` с `commandWindows`.
- MCP host registration документирован через `codex mcp add ... py -3 ... mcp_server.py --workplace ...`.

Не найдено:

- Windows login autostart через Task Scheduler.
- Windows service registration.
- Startup folder shortcut.
- Документированный `pf runtime install-autostart` / `uninstall-autostart`.
- Health/recovery policy для autostart после reboot.
- Инструкция, какой lifecycle должен autostart: MCP stdio server, PF Runtime HTTP service, Codex hooks, или всё вместе.

Вывод: Windows autostart requirements сейчас не специфицированы. Код поддерживает manual background start, но не persistent OS autostart.

## Рекомендации к правкам документации

1. Обновить `docs/concepts/runtime-mcp.md` и RU-версию как source-of-truth matrix:
   - tool name;
   - read/write status;
   - requires session или accepts `project_root`;
   - mutating guard (`apply: true`);
   - stable error codes.

2. Убрать безусловное “MCP read-only”:
   - заменить на “MCP facade is mostly bounded/read-oriented; governed mutation tools are limited to initialization/repair/work bootstrap and require explicit guard inputs”.

3. Развести три слоя Runtime:
   - short-lived CLI core;
   - Runtime Host file-first ticks/projections;
   - optional long-lived PF Runtime service with loopback HTTP, scheduler and background process.

4. Обновить known limitations:
   - “no required daemon” вместо “no daemon”;
   - отметить, что optional long-lived Runtime PoC exists;
   - явно сказать, что watch-events/network API/web UI/database scheduler не реализованы.

5. Добавить отдельный раздел “Windows startup/autostart”:
   - текущий статус: not implemented / manual start only;
   - supported manual command: `python bin/pf.py runtime start --workplace <workplace>`;
   - что autostart должен проверять через `runtime status`/`runtime doctor`;
   - что Codex MCP stdio registration не равен PF Runtime service autostart.

6. Синхронизировать RU docs с EN docs. Сейчас RU Runtime/MCP и hooks docs отстают по tool inventory и conversation capture semantics.