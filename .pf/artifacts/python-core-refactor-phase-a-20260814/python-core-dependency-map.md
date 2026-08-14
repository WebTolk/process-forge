# Статическая карта зависимостей Python Core

## Область и метод
Анализ ограничен разрешёнными файлами:

- `bin/pf.py`
- `tools/processforge.py`
- `tools/pf_runtime/__init__.py`
- `tools/pf_runtime/codex_hooks.py`
- `tools/pf_runtime/host.py`
- `tools/pf_runtime/mcp_server.py`
- `tools/pf_runtime/service.py`
- `schemas/*.json` (`105` JSON Schema-файлов)

Карта собрана по прямым `import`, топ-уровневым символам, прямым вызовам функций и явным adapter-seam. Это фактическая статическая картина, не reachability-модель выполнения.

## 1. Карта модулей

| Модуль | Строк | Top-level funcs | Classes | Methods | Imports | Локальные imports | Роль |
|---|---:|---:|---:|---:|---:|---:|---|
| `bin/pf.py` | 42 | 3 | 0 | 0 | 5 | 0 | тонкий launcher |
| `tools/processforge.py` | 26138 | 927 | 9 | 0 | 33 | 3 | монолитный core+CLI+orchestration |
| `tools/pf_runtime/__init__.py` | 6 | 0 | 0 | 0 | 1 | 0 | runtime protocol constant |
| `tools/pf_runtime/codex_hooks.py` | 114 | 4 | 0 | 0 | 10 | 0 | Codex hook adapter |
| `tools/pf_runtime/host.py` | 856 | 53 | 0 | 0 | 12 | 1 | local runtime host / projections / event ingress |
| `tools/pf_runtime/mcp_server.py` | 96 | 4 | 0 | 0 | 8 | 0 | read-only MCP facade |
| `tools/pf_runtime/service.py` | 695 | 34 | 1 | 10 | 20 | 4 | long-lived runtime service / loopback IPC |

Ключевой вывод: почти весь Python Core сосредоточен в `tools/processforge.py`; остальные модули являются thin-adapter слоями вокруг него.

## 2. Импортный граф

### 2.1 Основной монолит
`tools/processforge.py` импортирует только stdlib и `processforge_subprocess:*` на верхнем уровне (`tools/processforge.py:1-32`).
Связь с runtime вынесена в ленивые imports внутри CLI-обёрток:

- `from pf_runtime import service` в `command_runtime_*` на `18384-18453`
- `from pf_runtime import host` в `command_runtime_host_*` на `18456-18507`

Это явный seam: runtime не тянется в core на import-time, а подмешивается только при вызове команд.

### 2.2 Runtime adapter stack
Статические зависимости runtime-слоя однонаправленные:

- `tools/pf_runtime/service.py` -> `from . import host` (`27-28`)
- `tools/pf_runtime/host.py` -> только `from . import RUNTIME_PROTOCOL_VERSION` (`20`)
- `tools/pf_runtime/mcp_server.py` -> `from pf_runtime import host` (`31`)
- `tools/pf_runtime/codex_hooks.py` -> `from pf_runtime import host, service` (`72`)

Статического import-cycle между разрешёнными Python-модулями нет.

### 2.3 Динамические import seams
Есть три явных dynamic-import seam:

- `tools/pf_runtime/codex_hooks.py:19-21` + `31-32`
  - `sys.path.insert(...)`
  - `importlib.import_module("processforge")`
- `tools/pf_runtime/mcp_server.py:13-15` + `26-27`
  - `sys.path.insert(...)`
  - `importlib.import_module("processforge")`
- `tools/processforge.py:18385-18507`
  - ленивый `from pf_runtime import ...` внутри CLI wrappers

Это важная граница для рефактора: runtime/MCP сейчас не импортируют выделенный package API, они поднимают сам `processforge.py` как модуль.

## 3. Узлы с максимальным fan-in в `tools/processforge.py`

Топ прямых внутренних зависимостей:

- `check()` — `tools/processforge.py:2647` — fan-in `530`
- `rel()` — `tools/processforge.py:1073` — fan-in `415`
- `safe_id()` — `tools/processforge.py:1068` — fan-in `250`
- `as_list()` — `tools/processforge.py:12989` — fan-in `135`
- `now_utc()` — `tools/processforge.py:7480` — fan-in `103`
- `load_yaml_document()` — `tools/processforge.py:7677` — fan-in `101`
- `locate_flow_root()` — `tools/processforge.py:1268` — fan-in `97`
- `dump_yaml()` — `tools/processforge.py:1398` — fan-in `93`
- `require_flow_root()` — `tools/processforge.py:1272` — fan-in `76`
- `emit_process_event()` — `tools/processforge.py:10434` — fan-in `74`

Практически это четыре общих кластера:

- path/identity helpers: `safe_id`, `rel`, `locate_flow_root`
- YAML/document IO: `load_yaml_document`, `dump_yaml`
- diagnostics/checking: `check`, `print_checks`, `check_with_hint`
- event/time helpers: `now_utc`, `emit_process_event`

Это и есть фактическое “ядро ядра”, уже переиспользуемое многими подсистемами.

## 4. Узлы с максимальным fan-out в `tools/processforge.py`

Наиболее “оркестраторные” функции:

- `command_orchestrator_plan_apply()` — `19081` — fan-out `38`
- `build_project_context_snapshot()` — `9594` — `34`
- `command_task_create()` — `19402` — `26`
- `command_doctor_project()` — `19974` — `25`
- `resolve_specialization_context()` — `4757` — `24`
- `command_assignment_capsule()` — `11960` — `22`
- `command_supervisor_tick()` — `18173` — `22`
- `command_doctor_workplace()` — `2828` — `19`
- `command_session_start()` — `11145` — `18`
- `build_process_create_plan()` — `13929` — `18`

Вывод: самые широкие call-cluster находятся не в runtime-модулях, а в CLI/orchestration частях монолита.

## 5. Runtime-кластеры с высоким fan-in/fan-out

### 5.1 `tools/pf_runtime/host.py`
Главные внутренние узлы:

- fan-in:
  - `resolve_project()` — 9
  - `resolve_workplace()` — 7
  - `route_project()` — 7
  - `call_quiet()` — 5
  - `state_lock()` — 5
- fan-out:
  - `ingest_event()` — `556` — 13 вызовов
  - `tick_payload()` — `782` — 7
  - `command_init()` — `533` — 7
  - `work_state_payload()` — `694` — 5
  - `status_payload()` — `600` — 5

`ingest_event()` — главный runtime join-point: через него сходятся event normalization, ledger/session routing, projection rebuild и state persistence.

### 5.2 `tools/pf_runtime/service.py`
Главные внутренние узлы:

- fan-in:
  - `runtime_root()` — 7
  - `cleanup_stale_runtime()` — 7
  - `lock_path()` — 6
  - `http_json()` — 6
  - `inspect_lifecycle()` — 6
  - `runtime_request()` — 6
- fan-out:
  - `command_start()` — `497` — 7
  - `command_stop()` — `553` — 6
  - `command_doctor()` — `640` — 5
  - `inspect_lifecycle()` — `152` — 4
  - `cleanup_stale_runtime()` — `199` — 4

`service.py` изолирован вокруг process lifecycle + IPC и заметно уже `host.py`.

## 6. Глобальное состояние и mutable seams

Явных `global` statements в разрешённых Python-файлах не найдено, но есть module-level mutable state:

- `tools/pf_runtime/host.py:26`
  - `STATE_LOCK = threading.RLock()`
- `tools/pf_runtime/host.py:27`
  - `PROCESS_DEFINITION_CACHE`
- `tools/pf_runtime/host.py:226`
  - `PROJECTOR_BUILDERS`
- `tools/pf_runtime/codex_hooks.py:19-21`
  - mutation `sys.path`
- `tools/pf_runtime/mcp_server.py:13-15`
  - mutation `sys.path`

В `tools/processforge.py` верхний уровень в основном константный: `ROOT`, `PROJECT_FLOW_ROOT`, `PROCESSFORGE_VERSION`, `RELEASE_*`, `RESERVED_WORKER_ENV_KEYS` и т.д. (`35-188` и далее).

## 7. Циклы

### 7.1 Межмодульные
Статических циклов между разрешёнными модулями нет.

### 7.2 Внутрифункциональные / рекурсивные
Найдены рекурсивные/взаимно-рекурсивные узлы внутри `tools/processforge.py`:

- взаимная рекурсия:
  - `merge_parameter_value()` — `8261`
  - `merge_parameter_maps()` — `8286`
- саморекурсивные обходчики:
  - `deep_merge_dicts()` — `8234`
  - `redact_telemetry_value()` — `10156`
  - `answer_strings()` — `3569`
  - `expand_runtime_value()` — `17468`
  - `evolve_sanitize_value()` — `14881`
  - `worker_depends_on()` — `18549`
  - `validate_update_instance_against_schema()` — `20362`

Это не import-cycle, а recursive traversal helpers.

## 8. Schema-layer зависимость

`schemas/` — leaf-layer из `105` JSON Schema файлов.
Среди разрешённых Python-файлов schema-boundary в основном контролирует `tools/processforge.py`:

- distribution marker:
  - `looks_like_processforge_distribution()` — `1155-1164`
- process authoring plan validation:
  - `build_process_create_plan()` / `require_json_schema_document(...)` — `14024-14035`
- process doctor:
  - `append_json_schema_checks(...)` для `process-definition.schema.json` — `14546-14555`
- registry-schema resolution:
  - `registry_schemas` + `ROOT / "schemas" / schema_name` — `23500-23515`

Вывод: schema access централизован в монолите; runtime-adapters сами schema-слой почти не трогают.

## 9. Функции, реально общие для CLI, Runtime и MCP

### 9.1 Тонкие CLI точки входа
`bin/pf.py` не содержит бизнес-логики; он только делает `exec_processforge()` в `tools/processforge.py` (`bin/pf.py:18-33`).

Внутри `tools/processforge.py` runtime CLI команды — чистые делегаты:

- `command_runtime_*` -> `pf_runtime.service.*` (`18384-18453`)
- `command_runtime_host_*` -> `pf_runtime.host.*` (`18456-18507`)

### 9.2 Низкоуровневые core helper’ы, уже разделяемые несколькими поверхностями
Самые явные общие функции:

- `resolve_workplace_root()` — `tools/processforge.py:16047`
  - runtime service: `tools/pf_runtime/service.py:492, 498, 554, 628, 641, 658`
  - MCP: `tools/pf_runtime/mcp_server.py:81`
  - Codex hooks: `tools/pf_runtime/codex_hooks.py:78`
- `project_id()` — `tools/processforge.py:10231`
  - runtime host: `tools/pf_runtime/host.py:244, 376, 631, 827, 842`
  - MCP auth check: `tools/pf_runtime/mcp_server.py:42`
- `dump_yaml()` — `tools/processforge.py:1398`
  - runtime host read endpoints: `tools/pf_runtime/host.py:639, 690, 739, 778, 833`
  - runtime service passthrough: `tools/pf_runtime/service.py:665`
- `check()` / `print_checks()`
  - host projection doctor: `tools/pf_runtime/host.py:846-855`
  - runtime doctor: `tools/pf_runtime/service.py:644-654`

### 9.3 Runtime/MCP shared host payload API
`tools/pf_runtime/mcp_server.py` и runtime CLI сходятся на одних и тех же host readers:

- `project_state_payload()` — `host.py`
- `work_state_payload()` — `host.py`
- `resolve_payload()` — `host.py`
- `workplace_state_payload()` — `host.py`

Это уже готовая shared seam для выделения read-only Core API.

## 10. Что это значит для Phase A refactor

1. Главный источник связанности — `tools/processforge.py`; именно он определяет границы extraction.
2. `pf_runtime/*` уже достаточно thin и опирается на injection `core` вместо прямого static import из `processforge.py`; это хороший признак.
3. Первый кандидат на выделение в package API — не команды, а helper-кластеры:
   - path/id
   - YAML/document IO
   - checks/doctor primitives
   - event/runtime path helpers
4. Самые опасные shared seams:
   - `resolve_workplace_root()`
   - `project_id()`
   - `dump_yaml()`
   - `check()`
   - `load_yaml_document()`
   - `locate_flow_root()`
5. Самый плотный runtime join-point — `tools/pf_runtime/host.py:ingest_event`.
6. Самая плотная orchestration зона монолита — `command_*`/snapshot/task/supervisor участки, а не schema или launcher слой.
7. Для безопасного выноса Core package сначала нужно стабилизировать import seam:
   - убрать `importlib.import_module("processforge")`
   - убрать `sys.path.insert(...)`
   - заменить на явный package import поверх выделенного Python Core API.