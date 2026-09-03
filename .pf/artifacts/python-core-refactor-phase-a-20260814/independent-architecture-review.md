# Independent Architecture Review

## Вердикт

**pass_with_conditions**

Предложенная целевая архитектура в целом соответствует мастер-заданию: она фиксирует одно ядро, тонкие adapters и вынос общего Process-среза из `tools/processforge.py` в отдельный пакет (`python-core-target-architecture.md`). Но текущие артефакты ещё не закрывают несколько обязательных архитектурных рисков, и без явной доработки этих условий Phase B/C легко уйдёт в скрытую дубликацию и расхождение Runtime/MCP с Core.

## Что подтверждено

- Цель «одно ядро + несколько оболочек» совпадает с мастер-промптом и выбрана явно: `задания/process-forge-python-core-refactoring-master-prompt.md`, разделы 1, 12, 15, 20, 21, 31, 43.
- Выбранная схема `process-centric modular core + thin adapters` правильно направляет зависимости от `bin/pf.py`, `tools/processforge.py`, `tools/pf_runtime/*` к Core, а не наоборот: `.pf/artifacts/python-core-refactor-phase-a-20260814/python-core-target-architecture.md`, разделы «Выбор», «dependency rules», «Process Definition slice».
- Карта зависимостей подтверждает, что главный монолит и главный источник общих helper/API сейчас действительно `tools/processforge.py`, а не runtime-слой: `.pf/artifacts/.../python-core-dependency-map.md`, разделы 1, 3, 4, 9, 10.
- Runtime уже частично выделен, но остаётся адаптерным слоем над существующим Core/monolith, что согласуется с требованием «не переносить Runtime первым, а сначала убрать его зависимости от монолита»: `tools/processforge.py:18385-18507`, `tools/pf_runtime/service.py`, `tools/pf_runtime/host.py`, `tools/pf_runtime/mcp_server.py`, `задания/...`, раздел 20.

## Обязательные условия

### 1. Первый вертикальный срез должен быть действительно общим для CLI и Runtime/MCP
Сейчас это не доказано полностью в target architecture.

Почему:
- Process-срез выбран первым, и это правильно: `.pf/artifacts/.../python-core-target-architecture.md`, раздел «рекомендуемый первый slice».
- Но реальные runtime/MCP точки чтения и проекции завязаны на host API и продолжают тянуть Core через runtime adapter seam:
  - `tools/pf_runtime/codex_hooks.py:19-27, 60-83`
  - `tools/pf_runtime/mcp_server.py:13-27, 29-47`
  - `tools/pf_runtime/host.py:95-123, 227-236`
- В частности, `resolved_process()` в host уже вызывает `core.resolve_process_definition(...)`, а stage obligations используют deprecated aliases и process semantics внутри runtime host: `tools/pf_runtime/host.py:95-123, 125-160`.

Условие:
- Phase C должен вынести `resolve_process_definition`, authoring normalization, validation, doctor и route/handoff contract checks в Core API, который вызывается и из CLI, и из runtime host/MCP.
- Если первый slice останется только CLI-oriented, это будет нарушением разделов 12, 15, 16, 20 и 50 мастер-промпта.

### 2. Нужно жёстко отделить compatibility layer от нового Core
Сейчас риск скрытого compatibility-монолита высокий.

Почему:
- План cleanup корректно отмечает transitional aliases и deprecated поля: `.pf/artifacts/.../python-core-compatibility-cleanup.md`.
- Но runtime host по-прежнему читает и canonical field, и deprecated alias:
  - `automation_bindings` и fallback на `technical_obligations`: `tools/pf_runtime/host.py:145-160`
- Process doctor тоже продолжает принимать и только предупреждать по deprecated полям:
  - `gates` alias
  - `technical_obligations`
  - `handoff_required`
  в `tools/processforge.py` внутри `validate_process_contract(...)` и `command_process_doctor(...)`.

Риск:
- Если этот fallback переедет внутрь Core-моделей/сервисов, Core станет хранителем старых совместимостей, а не канонической семантики.

Условие:
- Deprecated alias/fallback должен остаться либо в adapter boundary, либо в отдельном compatibility-normalization слое с явно ограниченным сроком жизни.
- Внутренние Core-модели и сервисы должны работать только с canonical semantics.

### 3. В target architecture недостаточно явно зафиксирован runtime event/work-state boundary
Это главный риск для будущего расхождения CLI и Runtime.

Почему:
- Самый опасный join-point сейчас находится в `tools/pf_runtime/host.py::ingest_event`, а не в CLI: `.pf/artifacts/.../python-core-dependency-map.md`, раздел 5; `tools/pf_runtime/host.py`.
- Host держит mutable caches/state:
  - `STATE_LOCK`
  - `PROCESS_DEFINITION_CACHE`
  - `PROJECTOR_BUILDERS`
  в `tools/pf_runtime/host.py:20-27, 95-123, 226-236`
- Мастер-промпт отдельно требует разделять event semantics, envelope, persistence и transport: раздел 32.

Риск:
- Если Process Definition slice уедет в Core, а event/work-state semantics останутся размазанными по host, появится второй центр бизнес-логики.

Условие:
- До или сразу после первого Process slice нужно явно определить, что относится к:
  - domain semantics событий,
  - projection/work-state application services,
  - runtime transport/IPC.
- Иначе target architecture останется правильной только на бумаге.

### 4. Нужно запретить перенос utility-bucket в новый пакет под новым именем
Это реальный риск, а не теоретический.

Почему:
- Dependency map показывает очень высокий fan-in у общих helper-функций:
  - `check` `tools/processforge.py:2647`
  - `rel` `:1073`
  - `safe_id` `:1068`
  - `load_yaml_document` `:7677`
  - `dump_yaml` `:1398`
  - `locate_flow_root` `:1268`
- В target architecture вариант A прямо описан как риск utility-first extraction и отклонён. Это правильный вывод: `.pf/artifacts/.../python-core-target-architecture.md`, вариант A.
- Но выбранный вариант всё равно включает `common/paths.py`, `ids.py`, `yaml_io.py`, `checks.py`, и без строгой дисциплины это быстро превратится в новый `helpers/common`.

Условие:
- `common/*` должен оставаться минимальным инфраструктурным слоем.
- Любая функция с Process semantics, route semantics, doctor semantics, assignment/runtime meaning не должна попадать в `common/*`.

### 5. Нужно заранее закрыть Windows/import-path риск
Сейчас он подтверждён исходниками.

Почему:
- И `codex_hooks.py`, и `mcp_server.py` мутируют `sys.path` и делают `importlib.import_module("processforge")`:
  - `tools/pf_runtime/codex_hooks.py:19-27`
  - `tools/pf_runtime/mcp_server.py:13-27`
- Мастер-промпт отдельно требует проверить Windows, direct script entrypoints и import/package model: разделы 28, 29, 42.
- Target architecture это признаёт, но не фиксирует миграционный контракт достаточно жёстко.

Условие:
- Уже на bootstrap package shell нужен один канонический import path для runtime/MCP/hooks.
- Пока этого нет, нельзя считать import boundary устойчивым для дальнейшего extraction.

## Дополнительные замечания

- Признаков цикла `Core -> CLI/Runtime` в текущем предложении нет; напротив, правила зависимостей выписаны правильно. Но это пока декларация, не доказательство реализации.
- Признаков fake OOP или преждевременной hexagonal-переабстракции в выбранном варианте нет; отказ от варианта D выглядит обоснованным.
- Признаков требований к god service в target architecture нет, но риск есть вокруг будущих `application/*` фасадов. Их нужно держать как узкие use-case API, а не как новый монолит поверх пакетов.
- Runtime/CLI divergence уже существует частично по способу входа и доставки событий, но пока ещё контролируема, потому что runtime во многом читает функции monolith/Core, а не собственную независимую семантику.

## Итог

Архитектурное направление выбрано верно: **process-centric modular core + thin adapters**. Это лучший из предложенных вариантов для текущего состояния репозитория и он совместим с мастер-промптом.

Статус не `pass`, а `pass_with_conditions`, потому что до начала Phase B/C нужно явно закрепить пять вещей:

1. Первый slice обязан стать общим Core API для CLI и Runtime/MCP, а не только extraction из CLI.
2. Compatibility fallback нельзя переносить внутрь канонического Core.
3. Event/projection/work-state semantics нужно выделить из runtime host как отдельную границу.
4. `common/*` нельзя превращать в новый dumping ground.
5. Import-path модель для Windows/direct scripts/runtime hooks должна быть стабилизирована сразу на bootstrap package shell.

Если эти условия будут зафиксированы в следующем планирующем артефакте и соблюдены в implementation slices, дальнейший рефакторинг выглядит архитектурно жизнеспособным.