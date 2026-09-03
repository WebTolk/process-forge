# Декларативное исполнение процесса

ProcessForge исполняет Process YAML через единый `ProcessExecutionService`.
Определение процесса содержит только данные: без Python plugins, callbacks,
dynamic imports и исполняемого кода.

Обычный путь агента:

`pf.context -> pf.work.start(objective) -> pf.work.state -> работа ->
pf.work.transition(outcome, evidence) -> pf.work.state`

`pf.work.start` выбирает объявленную `initial_stage` либо первую executable
stage, а затем закрепляет эффективное Process definition, версию, fingerprint,
context snapshot и immutable Assignment capsule. Изменение Process YAML не
меняет уже начатый Run.

`pf.work.state` возвращает текущий контракт исполнения: Process, Run,
Assignment, stage, required inputs, obligations, artifacts, gates, blockers и
allowed outcomes.

`pf.work.transition` принимает outcome, evidence и optional notes. Линейный
маршрут следует порядку `stages[]`; минимальное ветвление задаётся
`outcomes[].next_stage`. Агент никогда не передаёт следующую stage, а
`process_transitions` остаются механизмом межпроцессных переходов.

Последний успешный transition завершает Assignment и Run, пишет summary и
handoff, обновляет projection и публикует события `process.stage.*`.
