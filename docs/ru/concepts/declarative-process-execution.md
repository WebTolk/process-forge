# Декларативное исполнение процесса

ProcessForge исполняет Process YAML через единый `ProcessExecutionService`.
Определение процесса содержит только данные: без Python plugins, callbacks,
dynamic imports и исполняемого кода.

Обычный путь агента:

`pf.context -> pf.work.start(objective, process_id?) -> pf.work.state -> работа ->
pf.work.transition(outcome, evidence, notes?) -> pf.work.state -> ... -> run_completed`

`pf.work.start` выбирает объявленную `initial_stage` либо первую executable
stage, а затем закрепляет эффективное Process definition, версию, fingerprint,
context snapshot и immutable Assignment capsule. Изменение Process YAML не
меняет уже начатый Run. При нескольких разрешённых процессах без явного выбора
возвращается `process_choice_required`: выберите предложенный `process_id` и
повторите start. `default` — рекомендация, а не автоматический выбор.

`pf.work.state` возвращает текущий контракт исполнения: Process, Run,
Assignment, stage, required inputs, obligations, artifacts, gates, blockers и
allowed outcomes.

`pf.work.transition` принимает outcome, evidence и optional notes. Линейный
маршрут следует порядку `stages[]`; минимальное ветвление задаётся
`outcomes[].next_stage`. Агент никогда не передаёт следующую stage, а
`process_transitions` остаются механизмом межпроцессных переходов.

## Свидетельства и восстановление после отказа

Например, стадия `task-result-fixation` может требовать артефакт `task-result`
и gate `all-blocking-tasks-completed`. Сначала создайте файл результата,
действительно проверьте блокирующие задачи и запишите результат проверки.
Затем передайте аргументы в `pf.work.transition`:

```json
{
  "project_root": "<project-root>",
  "outcome": "completed",
  "notes": "Результаты задач и проверки записаны; работа готова к ревью Run.",
  "evidence": [
    {"kind": "artifact", "id": "task-result", "path": ".pf/artifacts/result.md"},
    {"kind": "gate", "id": "all-blocking-tasks-completed", "status": "passed", "path": ".pf/artifacts/result.md"}
  ]
}
```

Это пример конкретной стадии: берите идентификаторы, обязательства и допустимый
outcome из своего `pf.work.state`. Пути относятся к корню проекта; файлы должны
существовать. Gate принимает `passed`, `approved` или обоснованный
`not_applicable`, но не `pass`. Запись gate — подтверждение выполненной проверки,
а не автоматическое доказательство смыслового качества документа.

Если evidence отсутствует или неверно, `transition_rejected` не продвигает
стадию. Прочитайте недостающие требования, выполните проверку, исправьте evidence
и повторите переход. Не обходите отказ ручной правкой YAML. После
`stage_transitioned` снова вызовите `pf.work.state` и продолжайте до ответа
`action: run_completed`, а не только до первого успешного перехода.

[Пример структуры state и перехода на английском](../../concepts/declarative-process-execution.md).

Последний успешный transition завершает Assignment и Run, пишет summary и
handoff, обновляет projection и публикует события `process.stage.*`.
