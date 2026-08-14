# Python Core Target Architecture

## Ограничения и опора
Анализ выполнен только по разрешённым источникам из Phase A. Числа fan-in/fan-out из `.pf/artifacts/python-core-refactor-phase-a-20260814/python-core-dependency-map.md` трактую как приближённые ориентиры для приоритизации extraction, а не как точную метрику выполнения.

Фактическая база для вариантов:
- процессный контракт и авторинг сегодня сосредоточены в `tools/processforge.py::resolve_process_definition`, `tools/processforge.py::normalize_process_authoring_answers`, `tools/processforge.py::process_from_authoring_answers`, `tools/processforge.py::validate_process_contract`, `tools/processforge.py::command_process_doctor`;
- runtime CLI уже является thin delegation-слоем: `tools/processforge.py::command_runtime_*` и `tools/processforge.py::command_runtime_host_*` передают управление в `tools/pf_runtime/service.py::*` и `tools/pf_runtime/host.py::*`;
- главный runtime join-point находится в `tools/pf_runtime/host.py::ingest_event`;
- read-only runtime/MCP seam уже фактически оформлен через `tools/pf_runtime/host.py::project_state_payload`, `work_state_payload`, `resolve_payload`, `workplace_state_payload`;
- самый токсичный seam для extraction сейчас не в process-domain, а в способе импорта core из runtime/MCP: `tools/pf_runtime/codex_hooks.py` и `tools/pf_runtime/mcp_server.py` используют `sys.path.insert(...)` и `importlib.import_module("processforge")`.

## Архитектурные варианты

### Вариант A. Utility-first extraction вокруг монолита
Суть: сначала вытащить общие helper-кластеры, не меняя предметные границы.

Предлагаемая структура:
```text
python_core/
  common/
    paths.py
    ids.py
    yaml_io.py
    checks.py
    time.py
  runtime/
    compatibility.py
tools/
  processforge.py
  pf_runtime/
```

Что переезжает первым:
- path/id helpers вокруг `tools/processforge.py::safe_id`, `rel`, `locate_flow_root`, `require_flow_root`;
- IO/helpers вокруг `load_yaml_document`, `dump_yaml`;
- diagnostics primitives вокруг `check`, `print_checks`;
- общие runtime helpers вроде `resolve_workplace_root`, `project_id`.

Правила зависимостей:
- `tools/processforge.py` может импортировать `python_core.common.*`;
- `tools/pf_runtime/*` может импортировать только `python_core.common.*`;
- `python_core.common.*` не импортирует CLI, runtime host/service, MCP.

Плюсы:
- минимальный стартовый риск;
- быстро убирает дублируемые зависимости runtime/MCP от монолита;
- удобно покрывать unit-тестами на чистых функциях.

Минусы:
- доменная структура ProcessForge не становится яснее;
- orchestration и process-contract logic остаются в `tools/processforge.py`;
- через 1-2 итерации может появиться “новый utility-bucket”.

Cycle risk:
- низкий, если запретить импорт из `tools/processforge.py` назад в `python_core.common.*`.

Migration cost:
- низкая.

Testability:
- высокая для helper-слоя;
- низкая/средняя для поведения процессов, потому что оно остаётся в монолите.

Suitability:
- CLI: хорошая как подготовительный этап.
- Runtime: хорошая для снятия `sys.path`/dynamic import боли.
- MCP: хорошая.
- Future Web: слабая, потому что Web не получает явной предметной API.

Вывод:
- полезен как технический prep-step, но слаб как целевая архитектура.

---

### Вариант B. Process-centric modular core с adapters сверху
Суть: выделить предметное ядро ProcessForge по доменам, а CLI/runtime/MCP оставить адаптерами.

Предлагаемая структура:
```text
src/processforge_core/
  common/
    paths.py
    ids.py
    yaml_io.py
    checks.py
    clock.py
  process_catalog/
    service.py
    models.py
  process_definition/
    authoring.py
    normalization.py
    schema_access.py
    validation.py
    models.py
  process_runtime/
    projection.py
    work_state.py
    handoff.py
    events.py
  worker_runtime/
    drivers.py
    launch.py
    run_state.py
  application/
    runtime_api.py
    process_api.py
    doctor_api.py

tools/
  processforge.py
  pf_runtime/
    host.py
    service.py
    mcp_server.py
    codex_hooks.py
bin/
  pf.py
```

Кандидатное распределение текущих символов:
- `resolve_process_definition` -> `process_catalog.service`;
- `normalize_process_authoring_answers`, `process_from_authoring_answers`, `build_process_create_plan` -> `process_definition.authoring` и `process_definition.normalization`;
- `validate_process_contract`, `command_process_doctor`-adjacent business logic -> `process_definition.validation` и `doctor_api`;
- `command_handoff_create` и route contract logic -> `process_runtime.handoff`;
- `tools/pf_runtime/host.py::ingest_event`, projections, current work state -> `process_runtime.events`, `projection`, `work_state`;
- `build_worker_process_command`, `write_agent_run_state` -> `worker_runtime.launch` и `run_state`.

Правила зависимостей:
- `common` не знает ни о чём выше;
- `process_catalog`, `process_definition`, `process_runtime`, `worker_runtime` могут зависеть только от `common` и друг от друга по направлению:
  - `process_catalog` -> `common`
  - `process_definition` -> `common`, `process_catalog`
  - `process_runtime` -> `common`, `process_definition`, `process_catalog`
  - `worker_runtime` -> `common`
- `application/*` координирует домены, но не содержит format/parsing CLI;
- `tools/processforge.py`, `tools/pf_runtime/*`, `bin/pf.py` зависят только от `application/*` и, где нужно, от публичных runtime API.

Плюсы:
- совпадает с реальной предметной группировкой из инвентарей;
- даёт отдельную API-поверхность для CLI, Runtime, MCP и будущего Web;
- позволяет убрать `importlib.import_module("processforge")` и передавать вместо монолита стабильный core package;
- вертикальные срезы можно вводить по доменам, а не по utility-файлам.

Минусы:
- требует жёсткой дисциплины по границам application vs adapters;
- есть риск преждевременно “размазать” orchestration по доменам;
- часть runtime фактов всё ещё завязана на файловую модель `.pf`, это нельзя прятать за слишком абстрактным service-layer.

Cycle risk:
- средний.
- Самые опасные места:
  - `process_definition.validation` <-> `process_runtime.handoff`;
  - `process_runtime.work_state` <-> `worker_runtime.run_state`;
  - `application.doctor_api` <-> `process_definition.validation`.
- Риск снимается, если:
  - handoff models лежат в `process_runtime.models` или `process_definition.models`, но в одном месте;
  - doctor API только оркестрирует, а не хранит правила;
  - worker lifecycle не знает о process authoring.

Migration cost:
- средняя.

Testability:
- высокая.
- Можно отдельно тестировать:
  - catalog/resolve;
  - authoring normalization;
  - contract validation;
  - event ingestion/projection/work-state;
  - worker launch/run-state.

Suitability:
- CLI: высокая.
- Runtime: высокая.
- MCP: высокая.
- Future Web: высокая, потому что Web сможет звать `application/*` или публичные service-модули без CLI-обёрток.

Вывод:
- это лучший кандидат на целевую архитектуру.

---

### Вариант C. Runtime-first split с общим core API
Суть: сначала стабилизировать runtime-подсистему как главный reusable backend, а process-domain оставить в монолите на второй фазе.

Предлагаемая структура:
```text
src/processforge_core/
  common/
  runtime_api/
    host_state.py
    service_lifecycle.py
    event_ingress.py
    projections.py
    mcp_read_api.py
  worker_runtime/
  compatibility/

tools/
  processforge.py
  pf_runtime/
```

Что переезжает первым:
- `tools/pf_runtime/host.py::*`;
- `tools/pf_runtime/service.py::*`;
- `tools/pf_runtime/mcp_server.py` переводится на package imports;
- worker lifecycle seam из `build_worker_process_command` и `write_agent_run_state`.

Правила зависимостей:
- runtime API не зависит от CLI;
- CLI только делегирует;
- process authoring/validation пока остаётся в `tools/processforge.py`.

Плюсы:
- быстро решает текущий технический долг runtime/MCP import seam;
- даёт стабильный backend для MCP и потенциального Web runtime-dashboard;
- затрагивает уже более thin-слой, чем process-contract part.

Минусы:
- целевое process-core остаётся невыделенным;
- появляется второй “полумонолит”: process logic отдельно, runtime logic отдельно;
- будущий Web для process authoring всё равно будет упираться в `tools/processforge.py`.

Cycle risk:
- низкий/средний.
- Основной риск между projections/work-state/event-ingress.

Migration cost:
- средняя.

Testability:
- высокая для runtime;
- средняя для общего продукта.

Suitability:
- CLI: средняя.
- Runtime: очень высокая.
- MCP: очень высокая.
- Future Web: средняя.

Вывод:
- хороший fallback, если цель ближайшей фазы только runtime stabilization, но не лучший общий target.

---

### Вариант D. Hexagonal application services
Суть: формально ввести порты/адаптеры для файловой системы, ledger, runtime transport и CLI/Web/MCP.

Предлагаемая структура:
```text
src/processforge_core/
  domain/
  application/
  ports/
  adapters/
    filesystem/
    runtime_http/
    mcp/
    cli/
```

Правила зависимостей:
- domain не знает о filesystem;
- application зависит от ports;
- adapters реализуют ports.

Плюсы:
- архитектурно “чисто”;
- лучшее основание для future Web и внешних интеграций.

Минусы:
- это выше текущей зрелости кода и задачи;
- слишком дорогая промежуточная абстракция для file-first продукта;
- велик риск псевдо-hexagonal слоя без реального упрощения.

Cycle risk:
- средний на бумаге, высокий practically из-за over-abstraction.

Migration cost:
- высокая.

Testability:
- потенциально высокая, но только после дорогой перестройки.

Suitability:
- CLI: средняя.
- Runtime: высокая.
- MCP: высокая.
- Future Web: очень высокая.

Вывод:
- не рекомендую как Phase A/B target; это скорее возможная Phase C эволюция после стабилизации modular core.

## Выбор
Рекомендую **Вариант B: Process-centric modular core с adapters сверху**.

Почему именно он:
- он лучше всего совпадает с уже наблюдаемыми seam-ами, а не придумывает новые;
- он отделяет предметные зоны ProcessForge, которые уже читаются в текущем коде и артефактах: catalog, definition/authoring/validation, runtime work-state/handoff/events, worker lifecycle;
- он сохраняет текущие thin adapters `bin/pf.py`, `tools/processforge.py::command_runtime_*`, `tools/pf_runtime/*`, вместо того чтобы втягивать их в domain;
- он даёт прямой путь убрать dynamic import из runtime/MCP, не требуя сразу полной hexagonal перестройки;
- он одинаково подходит для CLI, Runtime, MCP и будущего Web.

## Рекомендуемые dependency rules для выбранного варианта
1. `bin/pf.py`, `tools/processforge.py`, `tools/pf_runtime/*` не содержат предметных правил, только parsing, transport, formatting, delegation.
2. `processforge_core.common` не импортирует ничего из adapters.
3. `processforge_core.process_definition` не знает о runtime service/MCP/CLI.
4. `processforge_core.process_runtime` не знает о argparse, stdout/stderr, HTTP endpoint wiring.
5. `processforge_core.worker_runtime` не знает о process authoring и schema validation.
6. `processforge_core.application` координирует use-case сценарии, но не хранит низкоуровневые filesystem helpers.
7. Runtime/MCP/Codex hooks получают доступ к core только через package imports и явные service functions, без `sys.path.insert(...)` и без `importlib.import_module("processforge")`.

## Первый вертикальный срез
Первым вертикальным срезом рекомендую **Process Definition slice**, а не runtime slice.

Граница среза:
- каталог процесса;
- загрузка определения;
- authoring normalization;
- contract validation;
- process doctor;
- route/handoff contract checks, относящиеся к process-definition, но не runtime delivery.

Целевой пакетный срез:
```text
src/processforge_core/
  process_catalog/
    service.py
    models.py
  process_definition/
    authoring.py
    normalization.py
    validation.py
    schema_access.py
    models.py
  application/
    process_api.py
    doctor_api.py
```

Кандидаты на перенос в этот срез:
- `tools/processforge.py::resolve_process_definition`
- `tools/processforge.py::normalize_process_authoring_answers`
- `tools/processforge.py::process_from_authoring_answers`
- `tools/processforge.py::build_process_create_plan`
- `tools/processforge.py::validate_process_contract`
- логика из `tools/processforge.py::command_process_doctor`
- логика из `tools/processforge.py::command_process_route_validate`
- логика из `tools/processforge.py::command_process_route_doctor`
- осторожно выделяемая часть `tools/processforge.py::command_handoff_create`, только если она не требует runtime transport

Почему этот срез первый:
- он предметно связный;
- он опирается на стабильную схему `schemas/process-definition.schema.json`;
- он меньше зависит от live runtime lifecycle, чем `host.py::ingest_event`;
- он сразу создаёт reusable API и для CLI, и для future Web authoring/doctor;
- он позволяет позже подключить runtime-проекции к уже выделенной process model, а не наоборот.

## Phased migration для первого среза

### Phase 1. Stabilize imports and package shell
- создать package shell для `processforge_core`;
- вынести `common` primitives, которые нужны process-definition и runtime одинаково;
- не менять публичные команды;
- запретить новые прямые зависимости runtime/MCP на `processforge.py` кроме существующих переходных точек.

### Phase 2. Extract Process Definition slice
- перенести catalog/authoring/normalization/validation в package;
- оставить `tools/processforge.py` как adapter, который вызывает `application.process_api` и `application.doctor_api`;
- не трогать пока `pf_runtime/host.py::ingest_event`, `service.py`, MCP runtime-read API.

### Phase 3. Shared Process Definition API for CLI, runtime host, MCP facade, and hooks
- перевести `tools/pf_runtime/mcp_server.py` и `tools/pf_runtime/codex_hooks.py` на тот же Process Definition API, что и CLI;
- закрепить единый shared vertical slice для `CLI + runtime host + MCP facade + hooks`;
- не включать сюда event ingestion, projections, work-state, runtime transport и worker lifecycle.

### Phase 4. Extract runtime work-state/event slice
- переносить `ingest_event`, projections, `work_state_payload`, `project_state_payload`, `resolve_payload`, `workplace_state_payload`;
- после этого выделять worker lifecycle seam.

## Главные риски выбранного пути
1. Смешение domain и adapter responsibilities при переносе `command_*` функций целиком вместо переноса их business logic.
2. Преждевременное вытягивание `tools/pf_runtime/host.py::ingest_event` в первый срез. Это увеличит объём и риск циклов.
3. Сохранение compatibility surface внутри core package. В core нужно тащить canonical semantics, а compatibility aliases оставлять в adapter-слое.
4. Нечёткая граница между process-definition checks и runtime doctor checks. Их надо разводить сразу.
5. Попытка сделать полный hexagonal слой до стабилизации modular core.

## Краткий итог
Целевая архитектура для Python Core должна быть **process-centric modular core + thin adapters**. Лучший первый вертикальный срез - **Process Definition**: catalog, authoring normalization, validation, doctor API. Это даёт наиболее чистую предметную декомпозицию, минимальный цикл с runtime, хорошую тестируемость и прямую пригодность одновременно для CLI, Runtime, MCP и будущего Web.
