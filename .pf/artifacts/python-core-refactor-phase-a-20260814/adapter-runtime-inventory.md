# Inventory: Runtime–Python Core Adapter (фактологический отчёт)

## 1) Общая картина
- **Коротко:** runtime-подсистема разделена на CLI-оркестратор (Core) и runtime-ядро (host/service/mcp).
- **Основной исполнитель CLI:** `tools/processforge.py` (похоже на центральный dispatch-слой).
- **Структурный фокус:** управление worker-процессами, маршрутизация событий через Agent Ledger, PoC хост, HTTP-сервис рантайма и MCP-интеграция.

## 2) CLI (проценты, роутинг, команды)
- **Точка входа:** `bin/pf.py` -> `python tools/processforge.py`.
- **Роутинг команд в `tools/processforge.py`:**
  - `runtime ...` (serve/start/stop/restart/status/doctor/event/session-register/project-state/work-state/resolve/tick)
  - `runtime-host ...` (init/event/status/project-state/work-state/resolve/tick/rebuild-projections/projection-doctor)
  - `supervisor ...` (tick/run/status/stop)
  - `agent-director ...` (tick/status/stop)
  - `worker-run ...` (prepare/start/status/stop/collect/list; есть алиас `worker`)
  - `runtime-driver ...` (list/validate/describe; есть алиас `drivers`)
- **Ключевое наблюдение:** runtime-команды в CLI в основном делегируют в `pf_runtime.*` и не содержат собственную бизнес-логику маршрутизации событий.

## 3) Runtime (host/service)
- **PoC host:** `tools/pf_runtime/host.py`
  - хранение/загрузка состояния, маршрутизация сессий и проектов, прием событий, дедупликация событий.
  - `project_for_session`, `ledger_session` и проверка Project/Session из Agent Ledger (см. ограничения по сессии/проекту).
  - `command_tick` опционально дергает director и inspector.
  - projection-функции для stage obligations и rebuild.
- **Runtime service:** `tools/pf_runtime/service.py`
  - HTTP API на localhost/порт runtime; health-запросы и endpoints:
    - `/readyz`, `/status`, `/event`, `/session/register`, `/project-state`, `/work-state`, `/resolve`, `/tick`, `/shutdown`.
  - менеджмент жизненного цикла (старт/стоп/doctor), scheduler, статус heartbeat/lock.
  - авторизация токеном (`Authorization: Bearer ...`) для runtime API.
- **Интерфейс с codex/hooks:** thin wrapper в `tools/pf_runtime/codex_hooks.py` (попытка delivery в service -> fallback на host).

## 4) MCP
- **MCP сервер:** `tools/pf_runtime/mcp_server.py`
  - Тools: `pf.project_state`, `pf.work_state`, `pf.resolve`, `pf.workplace_state`.
  - Проверяет сессию/проект через ledger и отдает ошибки через `isError`.
  - В основном читает состояние runtime по API host/service.

## 5) Worker lifecycle
- **Запуск/передача параметров:** в `tools/processforge.py`
  - `worker_run_prepare` / `worker_run_start` / `worker_run_status` / `worker_run_stop` / `worker_run_collect`.
  - Команда собирается через `build_worker_process_command`.
  - Запуск через `subprocess.Popen` в `DETACHED_WORKER_PROCESSES`, state persistence через `write_agent_run_state`.
  - ENV для worker включает runtime-идентификатор и workspace-access.
- **Состояние рабочего цикла:** `start`/`status`/`stop`/collect централизованы в процессе runtime-команды, остановка — через pid/процессы в карте detached workers.

## 6) Runtime drivers
- Файл реестра: `templates/registries/runtime-drivers.yaml`
- Доступные встроенные драйверы:
  - `manual`
  - `generic-shell`
  - `codex-exec`
  - `test-echo-worker`
  - `test-shell-agent`
- CLI поддерживает `runtime-driver validate/describe/list`; есть проверки reserved env, heartbeat/limits/schemas в `tools/processforge.py` и `schemas/runtime-driver*.json`.

## 7) Inspector (надзор/наблюдение)
- В CLI и host присутствуют точки входа для tick supervisor:
  - `command_supervisor_tick`, `command_supervisor_run`, `command_supervisor_status/stop`.
- Host tick может включать вызов inspector-процедур через `host.tick_payload`.
- Прямая обязанность инспектора фиксируется как вызов наблюдательных/контрольных шагов в цикле tick, но не как отдельный устойчивый сервисный слой.

## 8) Agent Ledger / Agent Director / проекты
- **Agent Ledger:** используется как источник факта сессии/проекта:
  - в host маршрутизации и mcp авторизации.
  - проверка корректности session/project (`PermissionError` при mismatch).
- **Agent Director:** отдельные команды и tick-интеграция в host runtime.
  - CLI для director есть как отдельный блок; в runtime tick выполняется интеграция вызова director.
- **Projectors (обязательности этапов):**
  - реализация через host-проекции stage obligations и сбор их состояния для `/work-state`.
  - перестроение projections через `rebuild`/`tick` с опорой на process/assignment runtime-состояния.

## 9) current-work-state и события
- **`/work-state` и `command_work_state`:**
  - включает active sessions, current process/stage/task, workers, stage obligations/projections, session/event counters/пути.
- **События:**
  - event ingestion есть в host (`command_event`, `ingest_event`).
  - dedupe и нормализация событий реализованы в host.
  - codex_hooks нормализует события SessionStart/SessionEnd/PostToolUse и прокидывает в runtime/host.
  - в `service` есть `/event` endpoint + статус/сигнатуры доставки.

## 10) Точки зависимости от `tools/processforge.py`
- Почти все runtime-команды и lifecycle-операции инициируются/маршрутизируются через `tools/processforge.py`.
- `tools/pf_runtime/*` предоставляет реализацию runtime runtime-core, но не является единой точкой входа CLI.
- `tools/processforge.py` также владеет validation/resolve runtime driver и запуском worker-процессов — это **основной Core seam** для последующей декомпозиции.

## 11) Кандидаты для Core-facing seam (для рефакторинга/адаптера)
1. **Нормализация точки входа CLI**: вынести dispatch из `processforge.py` в отдельный adapter-слой и оставить runtime host/service как инвариантное ядро.
2. **Worker-launch layer**: выделить построитель запуска worker-а и env/pid/state handling из `processforge.py` (`build_worker_process_command`, `write_agent_run_state`, detached map).
3. **Route layer runtime host**: переместить командные entrypoints (`command_runtime_*`, `command_host_*`) в адаптер/интерфейс вызова, сохранить host как доменную реализацию.
4. **Event ingress abstraction**: унифицировать путь `codex_hooks -> runtime/service -> host.ingest_event`.
5. **Projector boundary**: вынести `work_state_payload`/`rebuild_stage_obligations` и projection-функции в явно выделенный projection module.
6. **Driver registry seam**: централизовать доступ к schema/registry/load/validate driver в отдельном модуле (сейчас частично смешан с CLI-логикой).
