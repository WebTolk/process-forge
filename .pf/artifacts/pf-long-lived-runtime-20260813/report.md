# PF Long-Lived Runtime Report

## Итог

Задание `задания/process-forge-long-lived-runtime-master-prompt.md` выполнено как следующий слой над PoC `runtime-host`: добавлен долгоживущий пользовательский процесс `PF Runtime`, один на workplace, с foreground/background CLI и loopback IPC. Бизнес-логика Ledger, Director, Inspector, event append и projection rebuild не дублируется в runtime service; service-слой делегирует её существующим PF Core/runtime-host функциям.

## Что реализовано

- `pf runtime serve` запускает foreground-процесс для одного workplace.
- `pf runtime start|stop|restart|status|doctor` управляют background-процессом без Windows Service/systemd/autorun.
- Singleton хранится в `workplace/runtime/pf-runtime/runtime.lock`; stale PID/lock очищаются перед новым стартом.
- Состояние процесса хранится в `workplace/runtime/pf-runtime/service.json`; token в `token.json`; operator/runtime logs в `workplace/runtime/pf-runtime/logs/`.
- IPC слушает только `127.0.0.1`, требует `Authorization: Bearer <token>`, ограничивает тело запроса `1 MiB` и не имеет endpoint для произвольных shell-команд.
- Health/status lifecycle: `starting`, `ready`, `degraded`, `stopping`, `stopped`, `failed`, `stale`.
- Project Router поддерживает несколько проектов и несколько сессий в одном workplace.
- Session-bound IPC-запросы блокируют чтение чужого `project_root` с HTTP `403`.
- Runtime scheduler вызывает существующие hosted ticks: Ledger maintenance, Agent Director и Execution Inspector; projection job оставлен future-ready.
- Старый `pf runtime-host ...` сохранён как lazy Core fallback при недоступном долгоживущем runtime.

## Codex Events Boundary

Использован локальный справочный материал `.pf/artifacts/pf-runtime-director-ledger-20260813/codex-events-reference.md`.

Текущий runtime принимает нормализованные события, совместимые с hook-событиями Codex: `SessionStart`, `UserPromptSubmit`, `PreToolUse`, `PostToolUse`, `PermissionRequest`, `PreCompact`, `PostCompact`, `Stop`, `SubagentStop`, `SessionEnd` и session registration через hook/cwd context. Transcript-файлы не используются как стабильный event API.

## Файлы

- `tools/pf_runtime/service.py` - lifecycle, singleton, IPC, scheduler loop, runtime doctor.
- `tools/pf_runtime/host.py` - reusable payload helpers для event/status/project/work/resolve/tick.
- `tools/processforge.py` - публичный CLI `pf runtime ...` и включение нового smoke в release-test registry.
- `tools/smoke_long_lived_runtime.py` - интеграционный smoke долгоживущего runtime.
- `.pf/artifacts/pf-long-lived-runtime-20260813/adapter-contract.md` - нейтральный контракт адаптеров для Codex и других ИИ-агентов.
- `.pf/assignments/long-lived-runtime-20260813.yaml` - assignment по схеме ProcessForge.
- `.pf/logs/pf-long-lived-runtime-20260813.md` - рабочий журнал.
- `.pf/handoffs/pf-long-lived-runtime-20260813-handoff.md` - handoff.

## Проверки

Пройдены:

- `python -m py_compile tools/processforge.py tools/pf_runtime/__init__.py tools/pf_runtime/host.py tools/pf_runtime/service.py tools/smoke_runtime_host_poc.py tools/smoke_long_lived_runtime.py`
- `python tools/smoke_long_lived_runtime.py`
- `python tools/smoke_runtime_host_poc.py`
- `python tools/smoke_agent_ledger.py`
- `python tools/smoke_agent_director_tick.py`
- `python tools/smoke_process_supervisor_tick.py`
- `python tools/validate-process-forge-schemas.py --root .`
- `python tools/validate-public-cleanliness.py --root .`
- `python tools/processforge.py events-validate --project-root .`
- `python tools/processforge.py runtime --help`
- `git diff --check` completed with only the existing Windows LF/CRLF warning for `tools/processforge.py`.

Дополнительный self-hook test:

- `pf runtime start --workplace D:\.agents\processforge-workplace --json` поднял runtime на `127.0.0.1`.
- Создание `.pf/artifacts/pf-long-lived-runtime-20260813/self-hook-runtime-test.md` текущей Codex-сессией не добавило событий в `.pf/runtime/events/events.ndjson`; count остался `39`.
- `C:\Users\musst\.codex\config.toml` содержит `notify = ... turn-ended`, но не содержит lifecycle hook bindings для `SessionStart`, `PreToolUse`, `PostToolUse`, `PermissionRequest`, `SessionEnd`.
- Manual normalized adapter event через runtime IPC успешно записался в project journal как `agent.tool.completed`, `source=processforge.runtime.codex-hooks-manual-selftest`.
- Вывод: runtime ingress работает, но реальные hooks текущей Codex-сессии в него ещё не подключены.

Не пройдено, но не исправлялось в этом задании:

- `python tools/validate-process-forge-checksums.py --root . --check` reports stale checksum inventory. Output includes pre-existing release files (`README.md`, `README.ru.md`, `VERSION`, update docs/index) and new runtime files (`tools/pf_runtime/*`, runtime smokes). Checksum refresh is a release inventory action and was not folded into this runtime implementation.

## Smoke Coverage

`tools/smoke_long_lived_runtime.py` проверяет:

- singleton start for one workplace;
- stale PID/lock recovery;
- graceful stop with persistent `stopped` status;
- crash/kill and restart recovery;
- bearer-token auth failure on unauthorized IPC;
- oversized IPC body rejection;
- two projects in one workplace;
- two Runtime/Codex sessions;
- session isolation and forbidden cross-project read;
- duplicate event handling;
- scheduler tick across organized/simple projects;
- active worker status surviving runtime crash/restart;
- runtime unavailable fallback via `runtime-host event`;
- CLI without runtime via project mode, Director tick, and Inspector tick;
- broken project B does not affect session-routed project A through fallback state;
- version mismatch detection through `runtime doctor`.

## Ограничения

- Это user-started local runtime. Автозапуск, Windows Service, systemd и machine-wide install намеренно не добавлялись.
- `projection` scheduler job сейчас future-ready marker; rebuild остаётся явной Core/runtime-host операцией.
- Hook adapter installation for live Codex is outside этого среза; runtime endpoint and normalized event ingestion are ready for that adapter.
