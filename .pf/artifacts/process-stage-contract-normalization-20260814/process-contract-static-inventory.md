# Отчёт: `process-contract-static-inventory` (статическая инвентаризация)

## 1) Process contract (Process Definition)

- Схема требует и валидирует базовые поля процесса: `schema_version`, `id`, `name`, `version`, `status`, `description`, `stages`, `roles`, `artifact_definitions`, `gates`, `evolution_policy` и др.
  Источник: [schemas/process-definition.schema.json](D:\Dev\process-forge\schemas\process-definition.schema.json#L6-L18), [schemas/process-definition.schema.json](D:\Dev\process-forge\schemas\process-definition.schema.json#L156-L175), [schemas/process-definition.schema.json](D:\Dev\process-forge\schemas\process-definition.schema.json#L178-L181).

- Поля процесса, связанные с исполнением и требованиями:
  - `required_capabilities`, `required_artifacts`, `required_evidence`, `acceptance`
  - `technical` части исполнения (`stage_completion`, `run_completion`, `runtime_requirements`, `runtime_execution_boundary`)
  - `process_transitions`
  - `hooks` (`emit`, `subscriptions`, `tracking`)
  - `forbidden_actions`
  Источник: [schemas/process-definition.schema.json](D:\Dev\process-forge\schemas\process-definition.schema.json#L109-L117), [schemas/process-definition.schema.json](D:\Dev\process-forge\schemas\process-definition.schema.json#L115-L181), [schemas/process-definition.schema.json](D:\Dev\process-forge\schemas\process-definition.schema.json#L265-L316).

- Конкретный канонический процесс `process-supervisor`:
  - `id: process-supervisor`, `execution_mode: orchestrated_agents`, статусы/способности, роли
  - 3 стадии: `prepare`, `start`, `collect`
  - 5 гейтов процесса (`assignment-ready`, `worker-run-ready`, `worker-run-finished`, `required-outputs-present`, `task-doctor-passed`)
  Источник: [processes/core/process-supervisor.yaml](D:\Dev\process-forge\processes\core\process-supervisor.yaml#L1-L13), [processes/core/process-supervisor.yaml](D:\Dev\process-forge\processes\core\process-supervisor.yaml#L51-L118), [processes/core/process-supervisor.yaml](D:\Dev\process-forge\processes\core\process-supervisor.yaml#L209-L228).

## 2) Stage contract (fields + usage)

- Схема стаджa (`stage`) требует минимум: `id`, `title`, `required_role`, `produced_artifacts`, `exit_gates`; также `required_inputs`, `required_artifacts`, `required_evidence`, `required_capabilities`, `entry_gates`, `exit_gates`, `hooks`, `technical_obligations`, `gates` и т.д.
  Источник: [schemas/process-definition.schema.json](D:\Dev\process-forge\schemas\process-definition.schema.json#L266-L314).

- В `process-supervisor` стадии объявлены с:
  - `required_inputs`, `produced_artifacts`, `required_role`, `required_capabilities`, `allowed_tools`, `entry_gates`, `exit_gates`, `gates`, `technical_obligations` у `collect`.
  Источник: [processes/core/process-supervisor.yaml](D:\Dev\process-forge\processes\core\process-supervisor.yaml#L52-L118).

## 3) Gate contract (fields + references)

- Схема гейта в process-definition содержит `id`, `description`, опциональный `blocking` и допускает произвольные поля.
  Источник: [schemas/process-definition.schema.json](D:\Dev\process-forge\schemas\process-definition.schema.json#L160-L171).

- Стадии ссылаются на гейты через `entry_gates`/`exit_gates`, а логику проверки для текущего процесса выполняет runtime-получатель (`stage_obligations`, см. ниже).
  Источник: [schemas/process-definition.schema.json](D:\Dev\process-forge\schemas\process-definition.schema.json#L283-L286), [processes/core/process-supervisor.yaml](D:\Dev\process-forge\processes\core\process-supervisor.yaml#L66-L73), [processes/core/process-supervisor.yaml](D:\Dev\process-forge\processes\core\process-supervisor.yaml#L89-L97), [processes/core/process-supervisor.yaml](D:\Dev\process-forge\processes\core\process-supervisor.yaml#L110-L117), [tools/processforge.py](D:\Dev\process-forge\tools\processforge.py#L13638-L13639).

## 4) Evidence / technical obligations inventory

- Контракт Evidence: `required_evidence` на процессе и на стадии; расширение через `acceptance.requires`.
  Источник: [schemas/process-definition.schema.json](D:\Dev\process-forge\schemas\process-definition.schema.json#L126-L127), [schemas/process-definition.schema.json](D:\Dev\process-forge\schemas\process-definition.schema.json#L127-L131).

- `technical_obligations` определяются на стадии как массив объектов с `id`, `projector`, `artifact`, `gate`, `source`, `verification`.
  Источник: [schemas/process-definition.schema.json](D:\Dev\process-forge\schemas\process-definition.schema.json#L286-L310).

- В `process-supervisor` стадия `collect` содержит 2 `technical_obligations`:
  - `required-output-readiness` → `required-outputs-present`
  - `task-doctor-verification` → `task-doctor-passed` с `verification` (`passed_event`/`failed_event`)
  Источник: [processes/core/process-supervisor.yaml](D:\Dev\process-forge\processes\core\process-supervisor.yaml#L118-L131).

- Runtime строит projector rows по этим obligation’ам через `required-output-readiness` и `verification-state` и кладёт их в `stage-obligations` projection.
  Источник: [tools/pf_runtime/host.py](D:\Dev\process-forge\tools\pf_runtime\host.py#L216-L226), [tools/pf_runtime/host.py](D:\Dev\process-forge\tools\pf_runtime\host.py#L228-L240).

## 5) Current-stage derivation (непосредственная)

- Явный вычислитель стадии в runtime: `active_stage(task, run_state)`:
  - `done/completed` ⇒ `""`
  - worker завершился (completed/failed/../cancelled) ⇒ `collect`
  - worker `running` ⇒ `start`
  - иначе `prepare`
  Источник: [tools/pf_runtime/host.py](D:\Dev\process-forge\tools\pf_runtime\host.py#L83-L93).

- Для каждого assignment деклараторного обзора берётся задача + состояние run, вычисляется `stage_id`, затем ищется совпавшая стадия процесса (`stage.get("id") == stage_id`) и берутся `technical_obligations`.
  Источник: [tools/pf_runtime/host.py](D:\Dev\process-forge\tools\pf_runtime\host.py#L119-L141).

- `current_work_state` в work-state payload берёт `active` из первой projection row и подставляет `active_process/active_stage` оттуда.
  Источник: [tools/pf_runtime/host.py](D:\Dev\process-forge\tools\pf_runtime\host.py#L668-L675).

## 6) Generic branches по `process_id`/`stage_id`

- Явное ветвление по конкретным stage-id в runtime минимально: только hardcoded стадии в `active_stage` (`prepare/start/collect`) и извлечение оттуда.
  Источник: [tools/pf_runtime/host.py](D:\Dev\process-forge\tools\pf_runtime\host.py#L83-L93).

- Построение execution-route из схемы процесса generic:
  - iterates all stages, берет `id`, `required_capabilities`, `required_artifacts`, `required_evidence`, `exit_gates` без привязки к конкретному процессу/стадии.
  Источник: [tools/processforge.py](D:\Dev\process-forge\tools\processforge.py#L4665-L4715).

- Единственный явный паттерн на основе конкретной именованной стадии в доке/валидации — поиск stage с подстрокой `review` при проверке размещения handoff в process-doctor logic.
  Источник: [tools/processforge.py](D:\Dev\process-forge\tools\processforge.py#L13649-L13653).