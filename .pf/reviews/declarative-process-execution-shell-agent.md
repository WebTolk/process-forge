# Независимый code review: declarative process execution

Скоуп обзора ограничен assignment capsule и `allowed_read_files`. Выполнен статический review без изменений кода и без запуска тестов.

## Findings

1. **Высокая**: `ProcessExecutionService` исполняет только часть декларативного контракта процесса, а часть уже существующих полей schema фактически игнорирует. Доказательства: schema объявляет `required_artifacts`, `required_evidence`, `stage_completion`, `run_completion` в корне и на уровне stage (`schemas/process-definition.schema.json:116-127`, `schemas/process-definition.schema.json:271-290`), но runtime при расчёте состояния и блокеров читает только `required_inputs`, `produced_artifacts`, `entry_gates`, `exit_gates`, `automation_bindings` (`src/processforge_core/process_execution.py:239-252`, `src/processforge_core/process_execution.py:582-618`), а `run_completion` обрабатывает только через `run_completion.gates` (`src/processforge_core/process_execution.py:682-690`). Риск: процесс может пройти stage transition при невыполненных `required_artifacts`/`required_evidence` или при правилах `stage_completion`, то есть фактический исполняемый контракт уже расходится с YAML вместо его полного использования.

2. **Средняя**: генератор agent-facing prompt всё ещё ведёт агента в запрещённый мастер-промптом ручной low-level workflow. Доказательства: `render_process_agent_prompt()` рекомендует `process-doctor` и `run-create` (`tools/processforge.py:14348-14353`), требует “Read the process definition before starting work” (`tools/processforge.py:14357`) и перечисляет stage ids (`tools/processforge.py:14365-14369`). Это противоречит целевому пути `pf.context -> pf.work.start -> pf.work.state -> pf.work.transition` и запрету заставлять агента читать весь YAML или создавать Run/Task вручную. Риск: live acceptance может падать не из-за core runtime, а из-за того, что сгенерированные инструкции продолжают провоцировать старый сценарий использования.

3. **Средняя**: schema событий не закрепляет обязательный контракт для stage lifecycle events, хотя runtime его уже эмитит. Доказательства: `process-event.schema.json` перечисляет `process.stage.started/completed/blocked/transitioned`, но поле `data` остаётся полностью свободным объектом без обязательных `run_id`, `assignment_id`, `process_id`, `stage_id`, `previous_stage_id`, `next_stage_id`, `outcome` (`schemas/process-event.schema.json:6-95`). При этом runtime действительно кладёт эти поля в payload (`src/processforge_core/process_execution.py:753-776`). Риск: любой другой эмиттер или будущая регрессия смогут записать “валидное” событие без обязательных данных, и schema это не остановит; это ослабляет проекторы и историю переходов.

4. **Низкая**: contract строки `recommendation` в текущем `pf.context` непоследователен относительно мастер-промпта. Доказательства: `CurrentWorkService.summary()` возвращает `"continue"` (`src/processforge_core/garage.py:236-243`), `guidance()` возвращает `"continue_governed_work"` (`src/processforge_core/garage.py:211-219`), а мастер-промпт ожидает `continue_work`. MCP фасад пробрасывает текущее значение как есть (`tools/pf_runtime/mcp_server.py:114-124`). Риск: агентские инструкции или клиенты, которые завязаны на точное значение рекомендации, будут интерпретировать состояние неоднозначно.

## Что подтверждено по коду

- Начальная стадия выбирается декларативно: сначала `initial_stage`, иначе первая executable stage; stage ids не захардкожены в core (`src/processforge_core/process_execution.py:23-36`, `src/processforge_core/process_execution.py:121-132`).
- `pf.work.start` для MCP и CLI использует `ProcessExecutionService`; старый bootstrap больше не дублирует логику процесса (`src/processforge_core/garage.py:221-228`, `tools/processforge.py:19992-19997`, `tools/pf_runtime/mcp_server.py:140-142`).
- `pf.work.transition` работает через `outcome`, а не через `next_stage`; линейный fallback и branching по `outcomes` реализованы (`src/processforge_core/process_execution.py:39-70`, `src/processforge_core/process_execution.py:323-329`).
- Блокировка перехода по exit/entry gates и automation obligations возвращает machine-readable blockers (`src/processforge_core/process_execution.py:331-345`, `src/processforge_core/process_execution.py:612-618`).
- `Assignment.stage` обновляется как durable state, история стадии сохраняется, финальный переход умеет завершать run (`src/processforge_core/process_execution.py:348-399`, `src/processforge_core/process_execution.py:692-717`).
- Pinning process definition на run реализован через snapshot/process fingerprint/capsule (`src/processforge_core/process_execution.py:435-453`, `src/processforge_core/process_execution.py:455-463`, `src/processforge_core/process_execution.py:726-736`).
- Канонические stage events реально эмитятся, и smoke support покрывает linear/blocked/evidence/events/final/pinning/branching сценарии (`src/processforge_core/process_execution.py:202-205`, `src/processforge_core/process_execution.py:390-398`, `tools/process_execution_smoke_support.py:132-212`).

## Остаточные риски и границы обзора

- Тесты не запускались: в рамках worker assignment выполнен только read-only review.
- Я не проверял файлы вне `allowed_read_files`, поэтому не подтверждаю фактическое состояние остальных acceptance artifacts, release-test и реальных project transcripts.
- Обёртки `smoke_process_execution_initial_stage.py` и `smoke_work_state_current_stage.py` упоминаются в release-командах (`tools/processforge.py:6939-6949`), но их содержимое не входило в разрешённый read scope этого задания.