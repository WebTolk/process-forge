# Инвентаризация `stage-projectors`

## 1) Проектор(ы) (projectors)

- В кодовой базе `tools/pf_runtime/host.py` реализован единственный runtime-проектор: `rebuild_projection(...)`, который строит табличную Markdown-проекцию из `events.ndjson`, фильтруя события с `event_type` начиная с `agent.`.
- Функция `projection_path(...)` в том же файле фиксирует путь артефакта проектора: `.pf/artifacts/projections/command-history.md` (через `core.locate_flow_root(project_root)`).
- `tools/pf_runtime/service.py` содержит задачу scheduler-а `projection` с периодом `30` секунд, но фактически статус по тику выставляется как `not_due` (без гарантии периодического пересоздания в этом слое).

## 2) Проекционные артефакты

- Основной артефакт: `command-history.md` (проекция команда/событие).
- Формирование/перестроение:
  - `runtime-host rebuild-projections` (`tools/processforge.py`) → `runtime_host.command_rebuild_projections(...)` → `tools/pf_runtime/host.py:command_rebuild_projections(...)`.
  - Каждому проекту соответствует запись `projection` со значением относительного пути к `command-history.md`.
- В целевом каталоге `.pf/artifacts/stage-projectors-next-20260814/` файл `static-inventory.md` пока отсутствует (по состоянию на проверку), требуемый артефакт нужно записать в итоговый отчёт.

## 3) Stage output / gate declarations (декларации этапов)

- Схема процесса определяет stage-поля:
  - обязательные: `id`, `title`, `required_role`, `produced_artifacts`, `exit_gates`;
  - объявленные поля: `required_artifacts`, `required_evidence`, `entry_gates`, `exit_gates`, `gates` (в `schemas/process-definition.schema.json`).
- По факту в репозитории:
  - 26 файлов из `processes/core/*.yaml` содержат `produced_artifacts`;
  - те же 26 файлов содержат `entry_gates/exit_gates`;
  - в этих процессных описаниях также присутствуют `required_outputs`-блоки (например, в `evolution_policy`).
- Примеры:
  - `processes/core/process-authoring.yaml: stages -> intake/draft-process/logic-review/apply-process` с `produced_artifacts`, `entry_gates`, `exit_gates`, `gates`.
  - `processes/core/knowledge-package-improvement.yaml` содержит `required_outputs` через `evolution_policy`.
  - `processes/core/project-onboarding.yaml`, `processes/core/context-resolution.yaml`, `processes/core/authoring-parity-audit.yaml` аналогично используют stage outputs/gates.

## 4) Типы событий

- Базовая схема `schemas/process-event.schema.json` задаёт enum `event_type` для события процесса:
  - `session.started`, `session.ended`, `session.message.recorded`, `chat.message.recorded`
  - `process.started`, `process.completed`, `stage.started`, `stage.completed`
  - `assignment.created`, `assignment.started`, `assignment.completed`
  - `artifact.created`, `artifact.updated`
  - `review.requested`, `review.completed`
  - `gate.passed`, `gate.failed`
  - `tool.invoked`, `tool.failed`
  - `mcp.invoked`, `mcp.failed`
  - `hook.dispatched`, `hook.failed`
  - `context.snapshot.refreshed`, `context.snapshot.stale`
  - `capability.missing`
  - `run.created`, `run.started`, `run.updated`, `run.summary.created`, `run.completed`, `run.failed`, `run.cancelled`, `run.doctor.passed`, `run.doctor.failed`
  - `task.created`, `task.started`, `task.updated`, `task.completed`, `task.failed`, `task.cancelled`, `task.doctor.passed`, `task.doctor.failed`
  - `iteration.added`, `iteration.started`, `iteration.completed`, `iteration.failed`
  - `process_authoring.started`, `process_authoring.answers.created`, `process_authoring.draft.created`, `process_authoring.logic_review.created`, `process_authoring.applied`, `process_authoring.completed`, `process_authoring.failed`
  - `process.created`, `process.doctor.passed`, `process.doctor.failed`
  - `authoring_parity.started`, `authoring_parity.process.checked`, `authoring_parity.resource.checked`, `authoring_parity.warning`, `authoring_parity.failed`, `authoring_parity.completed`
- В CLI/host-слое есть дополнительно ожидаемый список допустимых типов для некоторых операций: `REQUIRED_PROCESSFORGE_EVENT_TYPES` в `tools/processforge.py` (включает дополнительные события вроде `knowledge.resource.added`, `mcp.healthcheck.*`, `doctor.path.failed`, `package.*`, `workplace.*`, `project.*`, `template.*`, `knowledge_package.*`, `platform.*`, `run/task.*`, `iteration.*`, `authoring` и др.).

## 5) Doctor / MCP read-paths (чтение, диагностика, разрешения)

- Событийный журнал рантайма:
  - `core.event_runtime_paths(project_root)` → `.../.pf/runtime/events/events.ndjson` и `.../.pf/runtime/hooks/outbox`.
- Снимок контекста проекта:
  - `project_context_snapshot_paths(project_root)` → `.../.pf/contexts/project-context.snapshot.yaml` и `.../.pf/contexts/project-context.snapshot.md`.
- MCP server (`tools/pf_runtime/mcp_server.py`) — read-only инструменты:
  - `pf.project_state` → `project_state_payload(...)` (`core.project_context_check_result`, статус/политика);
  - `pf.work_state` → `work_state_payload(...)` (`events_path`, `event_count`, `supervisor`, сессия/наличие presence);
  - `pf.resolve` → `resolve_payload(...)` (разрешение проекта/ресурса из `resolved` snapshot);
  - `pf.workplace_state` → `workplace_state_payload(...)` (агентский ledger/presence по проектам).
- CLI-аналоги для чтения (без записи состояния):
  - `python tools/processforge.py runtime-host project-state`, `work-state`, `resolve`;
  - `python tools/processforge.py runtime status/work-state/project-state` (runtime service);
  - `python tools/processforge.py runtime-host rebuild-projections`, `runtime-host tick`.
- Doctor read-pathы:
  - `run-doctor --runtime-events` включает проверку `runtime/events/events.ndjson` (по `validate_run_consistency(..., include_runtime_events=True)`);
  - `doctor-project`, `doctor-workplace`, `project-doctor` используют соответствующие проверки манифестов/режимов и состояния, фиксируя `doctor`-события по процессу.