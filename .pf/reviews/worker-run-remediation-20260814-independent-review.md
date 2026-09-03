## verdict

- **PASS** — функционал ремедиации worker-run покрыт целевым кодом и smoke-сценариями.
- **WARN** — есть один технический остаточный риск, не являющийся фатальным для текущих проверок.

## evidence

- **PASS: Блокировка параллельного запуска между процессами**
  - `tools/processforge.py` введён `worker_run_lifecycle_lock` с `O_CREAT|O_EXCL` для файловой блокировки, путь `*.lifecycle.lock`.
  - `command_worker_run_prepare` и `command_worker_run_start` выполняются внутри этой блокировки.
  - При попытке второй сессии параллельного старта возвращается `SKIPPED` вместо создания второго запуска.

- **PASS: Подготовка (`prepare`) не влияет на активный запуск**
  - `prepare_worker_run` теперь удаляет устаревший `exit.json` перед подготовкой нового запуска.
  - В `tools/smoke_worker_run_shell.py` добавлен `prepare_while_running`: проверка, что при prepare на фоне RUNNING не меняются PID/маркер/статус.
  - Код наблюдаемости и выполнения также опирается на устойчивое состояние, снижая риск гонки в подготовке.

- **PASS: Восстановление через прямой путь инспектора**
  - `tools/processforge.py` добавлены helpers для прямых driver refs (`runtime_driver_ref_is_direct_path`, `normalized_runtime_driver_ref`, `runtime_driver_for_worker_state`).
  - `runtime_driver_for_worker_state` сначала использует `command["driver_ref"]`, затем fallback.
  - `build_worker_process_command` сохраняет `_driver_ref` в `command["driver_ref"]`, чтобы последующее наблюдение/сбор/стоп могли использовать прямой путь.
  - `observe_worker_run`, `command_worker_run_collect`, `command_worker_run_stop` переведены на state-driven резолвинг драйвера.

- **PASS: Очистка/детерминизм состояния**
  - Лок-файлы снимаются в `finally` блоках lock-контекста.
  - Smoke-скрипт содержит явный cleanup: стоп процесса при необходимости, закрытие терминала, удаление временных директорий/ресурсов.

- **PASS: Отсутствие регрессии legacy-сценария**
  - Поведение запуска теперь основано на текущем durable-состоянии и `command.driver_ref`.
  - Старые признаки «legacy» не являются обязательным рабочим путём; остаётся только безопасная обратная совместимость fallback при отсутствии прямой ссылки.

- **PASS: Нет изменений вне целевых зон**
  - По дифу трекаются только `tools/processforge.py` и `tools/smoke_worker_run_shell.py`, изменение сфокусировано на цели задания.
  - Отчёты в `.pf/artifacts/codebase-audit-20260814/*` содержат контур план/реализация/Smoke/регрессия по remediation (подтверждают предметный фокус).

- **PASS: Проверки срабатываний покрыты smoke-сценариями**
  - В `tools/smoke_worker_run_shell.py` добавлены:
    - duplicate start sequential,
    - duplicate start parallel с барьером,
    - prepare while running,
    - direct-path recovery.
  - Это даёт прямое подтверждение требований ревью.

## residual_risks

- **WARN:** при некорректном завершении процесса между `O_EXCL` lock-операцией и `finally` (например, hard crash/kill -9) lock-файл может остаться и заблокировать следующий старт до ручной очистки.
  Рекомендуется добавить TTL/cleanup дедлоков для lock-файла по времени жизни.
- **WARN:** прямой путь через fallback сохраняет «сосуществование» старого и нового источника источника драйвера; это корректно для совместимости, но расширяет матрицу состояний.
  Нужен дополнительный контроль состояния, если в будущем потребуется строгая деprecation политика для legacy-пути.