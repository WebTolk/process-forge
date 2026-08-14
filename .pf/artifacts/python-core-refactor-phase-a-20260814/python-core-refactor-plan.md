# План рефакторинга Python Core Process Forge

## Статус и рамки
План составлен по Phase A-артефактам и разрешённым исходникам. Код не изменялся.

Целевое направление:
- `process-centric modular core + thin adapters`
- один внутренний Python Core package
- CLI, Runtime, MCP и будущие точки входа используют один и тот же Core
- `tools/processforge.py` перестаёт получать новую предметную логику

## Обязательные условия перед Phase B/C
Независимый review дал `pass_with_conditions`. До начала кодового рефакторинга нужно считать обязательными пять условий:

1. Первый вертикальный срез обязан стать общим Core API для CLI и Runtime/MCP, а не только extraction из CLI.
2. Compatibility fallback нельзя переносить внутрь канонического Core.
3. Event/projection/work-state semantics нужно выделять как отдельную границу, а не оставлять размазанными по `tools/pf_runtime/host.py`.
4. `common/*` нельзя превращать в новый `helpers/common`.
5. Import-path модель для Windows, direct scripts, runtime hooks и MCP должна быть стабилизирована уже на bootstrap-фазе.

Без фиксации этих условий Phase B/C создаст второй скрытый монолит.

## Целевая пакетная форма
Рекомендуемая целевая форма после первых фаз:

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
    process_api.py
    doctor_api.py
    runtime_api.py

bin/pf.py
tools/processforge.py
tools/pf_runtime/
```

Правила зависимостей:
- Core не импортирует CLI, Runtime, MCP.
- `common/*` содержит только техническую инфраструктуру без process semantics.
- Compatibility normalization живёт вне канонических core-моделей.
- `tools/processforge.py`, `tools/pf_runtime/*`, `bin/pf.py` остаются адаптерами и делегатами.

## Порядок фаз

## Phase B. Bootstrap Core package
Цель:
- создать package shell и минимальную импортную модель без смены поведения

Содержимое:
- создать `src/processforge_core/`
- ввести минимальные `common/paths.py`, `ids.py`, `yaml_io.py`, `checks.py`, `clock.py`
- определить один канонический import path для:
  - `bin/pf.py`
  - `tools/processforge.py`
  - `tools/pf_runtime/codex_hooks.py`
  - `tools/pf_runtime/mcp_server.py`
  - `tools/pf_runtime/service.py`

Обязательные проверки до extraction:
- characterization для текущего запуска через `bin/pf.py`
- characterization для runtime/MCP import path
- direct `python tools/...` сценарии
- Windows paths и subprocess entrypoints
- release/archive включение нового package

Классификация среза:
- `behavior-preserving`

Review gate:
- импортный package shell работает без `sys.path.insert(...)`
- не появился цикл `Core -> adapters`
- release layout остаётся совместимым

## Phase C. Общий Process Definition API
Это первый обязательный предметный срез.

Переносить:
- `resolve_process_definition`
- `normalize_process_authoring_answers`
- `process_from_authoring_answers`
- `build_process_create_plan`
- `validate_process_contract`
- business logic из:
  - `command_process_doctor`
  - `command_process_route_validate`
  - `command_process_route_doctor`
- route/handoff contract checks, пока без runtime transport

Не переносить в этот срез:
- `tools/pf_runtime/host.py::ingest_event`
- runtime transport/IPC
- worker lifecycle

Тесты до extraction:
- process loading
- process normalization
- process validation
- process doctor
- process route validation
- process authoring parity со schema/template/examples
- compatibility cases для:
  - `technical_obligations`
  - `gates`
  - `handoff_required`

Классификация среза:
- базово `behavior-preserving`
- cleanup deprecated aliases только как отдельные подпакеты работ с явной пометкой

Review gate:
- CLI и Runtime/MCP вызывают один и тот же Process Definition API
- Core работает с canonical semantics
- compatibility слой не попал внутрь core-моделей
- старая логика не дублируется после переключения callers

## Phase D. Process Authoring integration
Цель:
- authoring использует тот же Core, что doctor и validator

Переносить/переключать:
- materialization и authoring-plan flow на `process_definition.authoring`
- schema access на `process_definition.schema_access`
- checks на `application.process_api` и `doctor_api`

Тесты до extraction:
- schema
- template
- answers
- materializer
- doctor
- docs/examples parity

Классификация среза:
- `behavior-preserving`
- если обнаружен баг в parity, отдельно помечать как `behavior-cleanup`

Review gate:
- нет второй авторинговой логики
- один source of truth для process contract semantics

## Phase E. Runtime read API и event/work-state boundary
Цель:
- снять главный риск расхождения Runtime/MCP с Core

Сначала определить и зафиксировать три отдельные зоны:
- event domain semantics
- projection/work-state application services
- runtime transport/IPC

Переносить:
- read-only surfaces вокруг:
  - `project_state_payload`
  - `work_state_payload`
  - `resolve_payload`
  - `workplace_state_payload`
- затем:
  - `ingest_event`
  - projections
  - work-state derivation

Тесты до extraction:
- runtime lifecycle smoke
- current-work-state
- projection freshness
- projection doctor
- MCP read facade
- ledger/session binding
- event ingestion effects before/after real action

Классификация среза:
- read API: `behavior-preserving`
- event/work-state cleanup: только с явной маркировкой каждого change set

Review gate:
- `tools/pf_runtime/host.py` перестаёт быть вторым центром process semantics
- нет новой дублирующей реализации work-state
- Core не импортирует runtime transport

## Phase F. Worker runtime and execution seams
Переносить:
- runtime driver resolution surface
- `build_worker_process_command`
- `write_agent_run_state`
- worker launch/run-state responsibilities
- затем только нужные execution seams вокруг task/assignment/inspector

Тесты до extraction:
- runtime drivers
- worker prepare/start/status/stop/collect
- codex-exec worker
- shell worker
- inspector boundary
- Windows subprocess behavior
- temp workspace behavior

Классификация среза:
- `behavior-preserving`
- intentional breaking changes здесь недопустимы без отдельного migration note

Review gate:
- нет дублирования driver logic
- lifecycle lock/state ownership явно определены
- Windows path/process behavior подтверждён

## Phase G. Thin adapters
Цель:
- сделать адаптеры действительно тонкими

Переключать:
- `bin/pf.py`
- `tools/processforge.py`
- `tools/pf_runtime/service.py`
- `tools/pf_runtime/mcp_server.py`
- `tools/pf_runtime/codex_hooks.py`

Правило фазы:
- новая предметная логика в `tools/processforge.py` не добавляется
- допустимы только dispatch, formatting, transport, wiring

Тесты до extraction:
- CLI smoke
- Runtime smoke
- MCP smoke
- direct scripts
- release smoke

Классификация среза:
- `behavior-preserving`

Review gate:
- адаптеры не содержат duplicate logic
- все вызовы идут в Core package API

## Phase H. Compatibility cleanup and duplicate removal
Удалять только после переключения всех callers и прохождения regressions.

Ранние слабые кандидаты:
- `smoke-all`
- `builtin-process-catalog-doctor --project-root`
- `gates`

Отложенные кандидаты:
- `handoff_required`
- legacy flat process layout
- `context-resolve`
- `context-compile`
- `supervisor*`
- `session-*` / `agent-*` пары
- `technical_obligations`

Правила удаления:
- сначала usage search
- затем docs/examples check
- затем migration note
- затем removal
- временный thin wrapper допустим
- duplicate logic недопустим

Классификация среза:
- cleanup alias without behavior change: `behavior-cleanup`
- удаление публичной или документированной совместимости: только `intentional breaking change`

Review gate:
- нет двух реализаций одного slice
- compatibility не растворена внутри Core
- удаление подтверждено артефактом миграции

## Characterization tests по срезам
Перед каждым extraction-срезом обязательно:

1. зафиксировать observable behavior
2. добавить или подтвердить smoke/regression
3. пометить change set как:
   - `behavior-preserving`
   - `behavior-cleanup`
   - `intentional breaking change`
4. только потом переносить код

Минимальный обязательный набор регрессий по всему плану:
- Process schema
- Process Doctor
- Process Authoring
- Process Stage contract normalization
- Process transitions/handoffs
- Runtime lifecycle
- Runtime Ledger/MCP
- Stage projectors
- verification/current-work-state
- worker-run shell
- codex-exec worker
- runtime drivers
- Agent Ledger
- Agent Director
- Inspector boundary
- release-check
- public cleanliness

## Package/import/Windows/release checks
Эти проверки должны повторяться после каждой фазы начиная с Phase B:

- import package из repo root
- import package в runtime hooks и MCP без `sys.path.insert(...)`
- `bin/pf.py` работает как canonical entrypoint
- `tools/processforge.py` остаётся внутренним adapter target, не публичным API
- direct `python tools/...` сценарии либо подтверждены, либо явно признаны transitional
- Windows paths
- subprocess execution
- temp workspace paths
- release archive включает новый package
- `.processforge-releaseignore` не вырезает нужный package

## Общие review gates
После каждой фазы обязательна независимая проверка на:

- behavior drift
- duplicate implementation
- circular dependencies
- Core importing CLI/Runtime
- God services
- fake OOP
- `misc/utils/common` dumping ground
- global mutable state expansion
- broken Windows/import paths
- silent compatibility layer
- Runtime/CLI divergence

## Критерии завершения первого этапа
Первый implementation-этап можно считать завершённым только если одновременно выполнено следующее:

1. Есть реальный Core package.
2. Первый предметный vertical slice полностью вынесен из монолита.
3. CLI использует этот Core без duplicate logic.
4. Runtime/MCP используют тот же Core или имеют уже реализованный общий migration path, а не декларацию.
5. В `tools/processforge.py` не добавлена новая предметная логика.
6. Не появилось новых циклических зависимостей.
7. `common/*` не стал новым dumping ground.
8. Windows/import/release checks зелёные.
9. Старый duplicate code выбранного slice удалён или сжат до thin wrapper.
10. Независимый review после remediation даёт `pass`.

## Рекомендуемая нарезка коммитов
Нужны небольшие slices, каждый в зелёном состоянии:

1. Bootstrap package shell и import stabilization.
2. Common infrastructure minimum.
3. Process Definition API extraction.
4. Process Authoring switch.
5. Runtime read API switch.
6. Event/work-state extraction.
7. Worker/runtime seams.
8. Adapter thinning.
9. Compatibility cleanup.

## Краткий вывод
Первым кодовым шагом должен быть не перенос Runtime, а bootstrap нового package и общий Process Definition API. Это единственная последовательность, которая одновременно закрывает требования мастер-промпта, замечания независимого review и риск скрытого второго монолита в Runtime.