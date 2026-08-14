# Architecture Reconciliation

## Статус
**Resolved**

Конфликт между target architecture и refactor plan снимается так:

- **Целевой вектор остаётся прежним:** `process-centric modular core + thin adapters`.
- **Первый общий вертикальный slice для CLI и Runtime/MCP обязателен уже в Phase C.**
- **Runtime/MCP/hooks не должны ждать отдельной Runtime-first фазы, чтобы начать использовать общий Process Definition API.**
- **При этом event ingestion, projections, work-state и runtime transport не входят в первый slice и остаются в runtime adapter seam до следующего отдельного среза.**

## Итоговое решение по границе B/C

### Phase B
Назначение Phase B: подготовить безопасный package/import фундамент, но **не переносить туда process semantics частями**.

В Phase B допустимо и нужно:

- создать bootstrap Core package shell;
- стабилизировать import/package path для `bin/pf.py`, `tools/processforge.py`, `tools/pf_runtime/codex_hooks.py`, `tools/pf_runtime/mcp_server.py`, `tools/pf_runtime/service.py`;
- сохранить `tools/processforge.py` и `tools/pf_runtime/*` как thin entry adapters;
- не менять observable CLI/runtime behavior.

В Phase B **не требуется**:

- переносить `ingest_event`;
- переносить projections/work-state;
- переносить runtime transport/IPC;
- переносить worker lifecycle.

### Phase C
Phase C фиксируется как **первый обязательный shared vertical slice**.

В него должны войти и перейти на общий Core API **все потребители process-definition semantics**:

- CLI;
- runtime host;
- MCP facade;
- Codex hooks path там, где им нужен process-definition resolution через runtime/host path.

Обязательный состав первого slice:

- `resolve_process_definition`
- `normalize_process_authoring_answers`
- `process_from_authoring_answers`
- `build_process_create_plan`
- `validate_process_contract`
- process doctor / route validation / route doctor business rules
- route/handoff contract checks, если это именно process-contract semantics, а не runtime transport

## Что остаётся adapter-only

До следующего отдельного slice adapter-only остаются:

- `tools/processforge.py` как CLI wiring/dispatch layer;
- `bin/pf.py` как launcher;
- `tools/pf_runtime/service.py` как runtime transport/service adapter;
- `tools/pf_runtime/mcp_server.py` как read-only MCP adapter;
- `tools/pf_runtime/codex_hooks.py` как lifecycle-hook adapter;
- `tools/pf_runtime/host.py` как runtime boundary для:
  - `ingest_event`
  - ledger/session authorization
  - projection rebuild orchestration
  - work-state assembly
  - workplace/project routing
- worker runtime surfaces:
  - `build_worker_process_command`
  - `write_agent_run_state`
  - driver resolution / launch / collect

Правило: adapter может вызывать Core API, но не должен дублировать или заново определять process-definition semantics.

## Что должно переключиться в первом vertical slice

В первом общем slice **обязательно** должны переключиться на один и тот же Process Definition API:

- CLI path из `tools/processforge.py`;
- runtime host path, который сейчас вызывает `core.resolve_process_definition(...)` и читает stage obligations;
- MCP read facade через host/runtime path;
- hooks/runtime delivery path косвенно, через тот же runtime/core contract, без отдельной process-логики внутри adapter.

Практический смысл решения:

- `resolve_process_definition` не остаётся “CLI-only extraction”;
- canonical interpretation `automation_bindings`, `gates`, `technical_obligations`, `handoff_required`, route/handoff contract checks должна определяться в одном Core API;
- runtime/MCP не должны продолжать жить на собственной локальной трактовке process contract после завершения Phase C.

## Что остаётся отложенным

До следующего среза явно откладывается:

- event domain semantics;
- `ingest_event`;
- projection model;
- work-state derivation;
- runtime read-model cleanup;
- runtime transport/IPC cleanup;
- worker lifecycle split;
- broad compatibility cleanup и removal of aliases.

Это уже **не Phase C**, а следующий slice уровня `Runtime read API + event/work-state boundary`.

## Required Gates

## Gate B. Bootstrap / import safety
Phase B считается завершённой только если выполнено всё ниже:

- package shell позволяет уйти от прямой зависимости на `sys.path.insert(...)` как архитектурной нормы;
- сохраняются текущие entrypoints:
  - `python bin/pf.py`
  - `tools/processforge.py`
  - runtime service / host / MCP / hooks launch surfaces
- нет нового направления зависимости `Core -> adapters`;
- release layout и public archive contract не сломаны новым package root.

## Gate C. Shared Process Definition API
Phase C считается завершённой только если выполнено всё ниже:

- CLI и Runtime/MCP используют **один и тот же** Process Definition API;
- canonical semantics определяются в Core, а не в adapters;
- compatibility cases читаются через Core boundary:
  - `technical_obligations`
  - `gates`
  - `handoff_required`
- route/handoff contract checks, относящиеся к process semantics, больше не живут отдельно в CLI-only logic;
- adapter code не содержит второй независимой трактовки process contract.

## Gate Next Slice. Runtime boundary
Следующий slice не должен стартовать как “продолжение C по инерции”; он должен открываться отдельно, когда зафиксированы:

- граница между process semantics и runtime event semantics;
- отдельная модель для projection/work-state;
- проверка, что read-only MCP surfaces сохраняют observable behavior:
  - `pf.project_state`
  - `pf.work_state`
  - `pf.resolve`
  - `pf.workplace_state`

## Compatibility Policy

В рамках этого reconciliation:

- compatibility fallback остаётся **вне canonical Core semantics**;
- Core должен читать legacy surface, но не проектироваться вокруг неё;
- удаление alias не входит автоматически в Phase B/C;
- cleanup alias возможен только отдельным change set после usage/docs/examples sweep.

Это относится минимум к:

- `technical_obligations`
- `gates`
- `handoff_required`
- transitional command aliases
- historical runtime/inspector naming

## Проверка по текущему коду

Текущее состояние кода подтверждает именно такую границу:

- runtime host уже использует `core.resolve_process_definition(...)` для process resolution;
- runtime host всё ещё держит у себя event ingestion, projection rebuild и work-state assembly;
- MCP facade является read-only adapter над host payload functions;
- hooks и MCP всё ещё завязаны на bootstrap import seam через `sys.path` / dynamic import;
- runtime CLI в `tools/processforge.py` уже выглядит как thin delegation к `pf_runtime.service` и `pf_runtime.host`.

Следствие: правильный следующий шаг не Runtime-first split, а **доведение общего Process Definition API до первого полного shared slice**, после чего отдельно открывается runtime boundary slice.

## Final Decision

1. **Phase B**: только bootstrap/package/import stabilization и thin-adapter preservation.
2. **Phase C**: первый общий vertical slice, в котором **CLI + Runtime/MCP/hooks** переходят на единый Process Definition API.
3. **Next slice after C**: event/projection/work-state/runtime transport boundary.
4. **Compatibility cleanup**: отдельно, не как скрытая часть extraction.
5. **Behavior must remain preserved** на всём протяжении B/C; breaking cleanup без отдельного migration decision не допускается.