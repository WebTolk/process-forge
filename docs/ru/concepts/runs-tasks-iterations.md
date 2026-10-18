# Run, Task и Iteration

![Управляемый цикл Work](../../assets/processforge-run-lifecycle.svg)

Process Definition описывает повторяемые правила. Run применяет процесс к
одному цельному результату. Task — поручение внутри Run, представленное
Assignment. Iteration фиксирует попытку работы внутри поручения, а не
автоматический переход стадии.

## Обычная управляемая Work

Для новой цели используйте `pf.context -> pf.work.start -> pf.work.state ->
работа и evidence -> pf.work.transition`. Следуйте возвращённому состоянию
до `action: run_completed`. Сохраняйте точные Run/Assignment/context из ответа,
проверяйте разрешения и передавайте селекторы в каждый вызов Work без привязанной
сессии. Для прежней работы используйте [продолжение](work-continuation.md).
Последний переход сам пишет summary и handoff; сессия приложения остаётся
отдельной. См. [Garage Core](garage-core.md) и
[примеры evidence](declarative-process-execution.md).

## Долговечные записи

- Определения процессов находятся в `processes/user/<process-id>.yaml`;
  официальный процесс может поставляться пакетом.
- Run хранится в `.pf/runs/<run-id>/run.yaml`.
- Summary — `.pf/runs/<run-id>/summary.md`, передача результата —
  `.pf/handoffs/runs/<run-id>-handoff.md`.
- Task использует `.pf/assignments/<task-id>.yaml` и поле `run_id`.
- Итерации хранятся в YAML Assignment. Виды: `work`, `debug`, `fix`, `review`,
  `test`, `research`, `handoff`, `note`. Статусы: `planned`, `in_progress`,
  `completed`, `passed`, `failed`, `cancelled`.

Публичные записи не должны содержать секреты или локальные абсолютные пути.
Граница Run и вложенная работа описаны в [модели выполнения](process-definition-run-task-iteration.md).

## Расширенный batch-сценарий

Ручные `run-create`, `task-create`, `iteration-add`, `task-complete`,
`run-summary`, `run-doctor`, `run-complete` управляют явными записями batch.
Полная последовательность приведена в [batch-руководстве](../getting-started/task-batch-workflow.md).
Это отдельный сценарий: его команды не добавляются к обычному завершению
управляемой Work. Одна запись Iteration не продвигает стадию.

События проекта используют `.pf/runtime/events/events.sqlite3`. Хуки могут
создавать файлы outbox по совпавшему типу события. Файловые команды не требуют
демона, планировщика или аренды; необязательный app-server не делает их
фоновыми заданиями автоматически.
