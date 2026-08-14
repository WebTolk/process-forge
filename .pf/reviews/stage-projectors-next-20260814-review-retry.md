# Независимая проверка stage projector

## Вердикт
**PASS** — декларативный проектор реализован корректно, ключевые сценарии покрыты и подтверждены артефактами/тестами.

## PASS (доказательства)
- `process-supervisor` объявляет в `collect` техническое обязательство `required-output-readiness` с артефактом `stage-obligations` и гейтом `required-outputs-present`.
  `[processes/core/process-supervisor.yaml](/D:/Dev/process-forge/processes/core/process-supervisor.yaml:118)`
- Runtime Host строит обязательства строго из declaration/assignments/состояния инспектора: `declared_stage_obligations` читает `technical_obligations` из процесса по `core.task_process_id`, без stage-specific логики в рантайме.
  `[tools/pf_runtime/host.py](/D:/Dev/process-forge/tools/pf_runtime/host.py:104)`
- Для каждой активной задачи projector собирает `required_outputs`, добавляет `expected_report`, вычисляет `readiness` и `source_fingerprint`, пишет `.pf/artifacts/projections/stage-obligations.json` через `rebuild_stage_obligations`.
  `[tools/pf_runtime/host.py](/D:/Dev/process-forge/tools/pf_runtime/host.py:137)`
  `[tools/pf_runtime/host.py](/D:/Dev/process-forge/tools/pf_runtime/host.py:171)`
- `projection-doctor` возвращает PASS/FAIL по статусу `current/missing/stale/invalid` и используется в тестах.
  `[tools/pf_runtime/host.py](/D:/Dev/process-forge/tools/pf_runtime/host.py:697)`
- `smoke_stage_projectors.py` валидирует ключевые состояния проектора: `missing`, `stale`, удаление/пересборка, защиту semantic-artifacts и присутствие обязательства в `work-state`.
  `[tools/smoke_stage_projectors.py](/D:/Dev/process-forge/tools/smoke_stage_projectors.py:68)`
  `[tools/smoke_stage_projectors.py](/D:/Dev/process-forge/tools/smoke_stage_projectors.py:81)`
  `[tools/smoke_stage_projectors.py](/D:/Dev/process-forge/tools/smoke_stage_projectors.py:115)`
- Локальные подтверждающие артефакты показывают проходы `py_compile`, `schema validation`, `smoke_stage_projectors`, `projection-doctor`, Codex hook + runtime restart + `pf.work_state`.
  `[.pf/artifacts/stage-projectors-next-20260814/implementation-report.md](/D:/Dev/process-forge/.pf/artifacts/stage-projectors-next-20260814/implementation-report.md:30)`
  `[.pf/artifacts/stage-projectors-next-20260814/live-validation.md](/D:/Dev/process-forge/.pf/artifacts/stage-projectors-next-20260814/live-validation.md:23)`

## FAIL/замечание (неблокирующее для проверки)
- Единственное обнаруженное ограничение: после `runtime restart` первый `runtime work-state` иногда даёт HTTP timeout, но повторный запрос после завершения scheduler pass возвращает тот же `current` projection; durability не нарушена.
  `[.pf/artifacts/stage-projectors-next-20260814/live-validation.md](/D:/Dev/process-forge/.pf/artifacts/stage-projectors-next-20260814/live-validation.md:33)`
  Это требует повторной отправки запроса/ожидания после рестарта, но не фиксирует логический дефект самого projector.