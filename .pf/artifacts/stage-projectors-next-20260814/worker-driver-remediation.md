# Remediation: живое наблюдение shell worker

Дата: 2026-08-14

## Воспроизведённые дефекты

При живом Runtime supervisor независимый `codex-exec` worker был ошибочно
наблюдён как `manual`: supervisor брал run default вместо уже записанного в
agent-run state `driver_id`. Это заменяло лимит `3600` секунд на `30` и
преждевременно завершало worker.

При повторной подготовке того же task старый durable `exit.json` оставался на
месте, поэтому Inspector мог принять результат предыдущей попытки за результат
нового PID.

## Исправление

- `command_supervisor_tick()` теперь при наблюдении предпочитает durable
  `state.driver_id`, затем worker/task/default driver.
- `prepare_worker_run()` удаляет только свой старый `exit.json` перед созданием
  новой попытки. Другие durable facts и semantic artifacts не затрагиваются.

## Живое подтверждение

После restart Runtime и нового prepare повторный reviewer-worker сохранён как
`driver_id: codex-exec`, `timeout_seconds: 3600`, `status: running`, с новым
PID и heartbeat. Его итоговый review собирается отдельным PF lifecycle.

В ходе проверки найден и устранён связанный driver defect: detached Codex
worker не публиковал `exit.json`, поэтому Inspector не мог отличить успешный
процесс от `unknown_exit`. См. `codex-exit-contract-remediation.md`.
