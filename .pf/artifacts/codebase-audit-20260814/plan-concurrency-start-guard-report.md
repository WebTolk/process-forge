## implementation_points

### Точки изменения (без изменения логики driver/runtime)

1. **Точка входа**: `command_worker_run_start` (в `tools/processforge.py`, строка ~17673)
   - Добавить ранний check состояния **до** `prepare_worker_run(...)`.
   - Это единственное место, где дублирующийся `start` происходит в CLI path; сейчас оно всегда вызывает `prepare_worker_run`, тем самым перезаписывая `status` и роняя PID от уже живого воркера.

2. **Текущее состояние и источник истины**: `load_agent_run_state` + `observe_worker_run`
   - Для уже запускающегося/запущенного воркера читать существующий `status.json` через `load_agent_run_state`.
   - Если `status == "running"`, дополнительно прогонять через `observe_worker_run(...)` и только после этого принимать решение:
     - если после reconcile всё ещё `running` → no-op и возврат успешного codepath;
     - если перейдёт в terminal (`completed|failed|timed_out|unknown_exit|lost`) — позволить обычный запуск новой попытки.
   - Это делает старт идемпотентным и не требует изменения схемы.

3. **Новый статус-марк `starting` (опционально, но минимально и совместимо)**
   - Вставить короткую метку до фактического `Popen`, например:
     - `write_agent_run_state(..., status="starting", pid=None, started_at=now_utc(), ...)`
   - Расширить `AGENT_RUN_START_SKIP_STATUSES`, если решено учитывать конкурирующие параллельные старты в пределах одного процесса:
     - `{"starting", ... }`
   - Это убирает “перехлёстывание” при многопоточном запуске внутри одного runtime- процесса (если `status` уже успел обновиться).

4. **Idempotency-результаты запуска**
   - `command_worker_run_start` должен явно различать:
     - **duplicate while running**: `returncode=0`, без перезапуска процесса;
     - **already terminal**: `returncode=1` (или чёткий ранний `return`) с текстом “already terminal”;
     - **manual**: сохранить текущее поведение (`MANUAL` и `ready`).
   - Смысловая совместимость: пользовательский контракт не меняется, меняется только повторный вызов на уже работающем запуске.

5. **Минимальная корректировка наблюдаемости**
   - При no-op-дедупликации добавить явное событие/логику:
     - `emit_process_event(..., "worker.run.start_skipped")` или расширить текущий `print`.
   - Это полезно для аудита и доказательства, что второй старт распознан как дубль, а не проигнорирован молча.

### Почему это “smallest compatible”
- Меняется только `tools/processforge.py`.
- Не меняется интерфейс CLI (флаги `--detach/--wait` и т.п. остаются).
- Непосредственно покрывает известный дефект из `findings-validation.md` (дублирующийся `start`), без пересборки схем/драйверов.

---

## state_transition

Текущий жизненный цикл (`AGENT_RUN_STATUSES`, `tools/processforge.py`, строка ~17005):

- `planned | ready | starting | running | completed | failed | timed_out | unknown_exit | lost | blocked | blocked | manual_required`

Текущие переходы в коде:
- `prepare_worker_run` → `ready` / `manual_required`
- `command_worker_run_start` → `running` (после `Popen`)
  - при `detach=True`: остаётся до завершения наблюдения
  - при `detach=False`: сразу в `completed/failed` после `wait`
- `observe_worker_run`:
  - если есть `exit.json` → `completed|failed`
  - таймаут → `timed_out`
  - “pid умер без exit” → после grace `unknown_exit`
  - `running` сохраняется, пока процесс жив

### Предлагаемая матрица старта (idempotent)

- `running` (живой pid) → **no-op success**, состояние не меняется (или мягкий `starting` → `running` не применяется)
- `running` + pid не жив → через `observe_worker_run` в reconcile-состояние:
  - если `unknown_exit/failed/...` → старт разрешён
- `ready/manual_required/starting` → продолжить `prepare_worker_run` + старт
- terminal (`completed/failed/timed_out/unknown_exit/lost/cancelled`) → запрет/ошибка старта без ручной очистки

### Точные символы для реализации
- `AGENT_RUN_START_SKIP_STATUSES`
- `AGENT_RUN_FAILURE_TERMINAL_STATUSES`
- `command_worker_run_start`
- `prepare_worker_run`
- `write_agent_run_state`
- `observe_worker_run`
- `load_agent_run_state`
- `process_pid_running`

### Резидуальные гонки (остаются возможными)
- **TOCTOU между двумя конкурентными стартами до фиксации `starting`**: без межпроцессного lock (flock/atomic rename lockfile) два процесса могут пройти проверку и запустить два `Popen`.
- **Одновременный `start` + `prepare` из внешнего сценария**: если внешний вызов явно делает `worker-run prepare` между проверкой и стартом, возможен перезапись-момент.
- **Файловая гонка записи `status.json`**: текущая запись через `json_write` не защищена блокировкой.
- **Zombie/невалидный pid-отчёт**: `process_pid_running` может быть ложноположительным при ограничениях ОС/платформы.

---

## regression_design

Все проверки детерминированы и ориентированы на текущее поведение `worker-run start` и `command_worker_run_status`.

1. **Duplicate start на живом воркере (главной ветки)**
   1. Подготовить задачу с рабочим shell-воркером (например, `sleep`), как в текущем `findings-validation.md`.
   2. Запустить `worker-run start --project-root ... --task ... --driver <sleep-driver> --detach`.
   3. Сразу выполнить тот же `worker-run start` ещё раз.
   4. Ожидаем:
      - второй запуск не должен менять `status` на новый `running` с другим pid;
      - второй `returncode` должен быть `0` (или согласованно-определённый no-op), а не перезапускать процесс.
      - `status.json` после двух запусков содержит один `pid` и статус `running`.

2. **Concurrent start race window (два параллельных процесса)**
   1. Запустить два параллельных процесса с одинаковым `worker-run start ... --detach`.
   2. Проверить `status.json` и `stdout/stderr` после завершения обоих вызовов.
   3. Ожидаем:
      - не более одного живого воркера для `run_id/task_id`;
      - второй вызов детерминированно попал в `start skip` (no-op/ожидаемо-завершённый ответ).
   4. Фиксируем как ожидаемое поведение после изменений; если останется двойной запуск, это подтверждает необходимость file-lock уровня guard.

3. **Transition from stale running (перезапуск после детекта)**
   1. Запустить detach-воркер.
   2. Убить его pid вне PF (или дождаться, если короткий sleep).
   3. Дать `observe`/`status` пройти 0.25s grace window для `unknown_exit`.
   4. Повторный `start` должен разрешиться только после того, как reconcile перевёл состояние в non-running.
   5. Ожидаем: новый pid только после реального terminalization предыдущей попытки.

4. **Сигнализация terminal-статусов**
   1. Запустить короткий `worker-run start --wait` чтобы получить `completed`.
   2. Немедленно вызвать `worker-run start` повторно.
   3. Ожидаем: отказ/skip с явным сообщением terminal и без нового процесса.

5. **Стабильность наблюдателя**
   1. Для уже запущенного процесса вызывать периодический `command_worker_run_status`.
   2. Убедиться, что dedupe-ветка не влияет на публикацию `worker.run.finished` и на существующие статусы завершения (`completed`/`failed`/`unknown_exit`).
