# Реализация remediation для `worker-run`

Дата: 2026-08-14
Статус: PASS

## Реализовано

- `worker-run start` и `worker-run prepare` используют межпроцессный lifecycle
  lock на уровне одной пары `run_id/task_id`. Повторный живой start возвращает
  `SKIPPED`, не меняя PID и durable command/state.
- Direct-path driver сохраняет нормализованный `driver_ref` в private runtime
  `command.json`. Inspector, stop и failure collection разрешают его до
  fallback на обычный `driver_id`.
- Generic shell smoke проверяет последовательный и действительно параллельный
  duplicate start, prepare при живом worker-е и Inspector recovery для driver-а
  вне project root.
- По прямому указанию оператора legacy regression удалена; public-release
  migration/deprecation логика не добавлялась.

## Process Forge исполнение

Шесть shell-worker sessions завершены и собраны Inspector-ом:

- один implementation worker `gpt-5.5` для `tools/processforge.py`;
- четыре implementation/correction workers `gpt-5.3-codex-spark` для
  `tools/smoke_worker_run_shell.py`;
- один read-only independent reviewer `gpt-5.3-codex-spark`.

В ходе финального review были обнаружены и исправлены ошибки первых тестовых
изменений: удалён лишний legacy scenario, восстановлен реальный collect в
environment case и заменена сериализованная имитация гонки на barrier-based
parallel start.

## Проверки

Все PASS:

- `python tools/smoke_worker_run_shell.py`;
- `python tools/smoke_runtime_driver_registry.py`;
- `python tools/validate-process-forge-schemas.py --root .`;
- `python tools/processforge.py runtime-driver validate --project-root . --driver codex-exec`;
- `python -m py_compile tools/processforge.py tools/smoke_worker_run_shell.py`;
- `python tools/processforge.py release-test --root . --only smoke_worker_run_shell --no-clean`;
- `python tools/processforge.py release-check --root .`;
- `git diff --check` (только существующие LF→CRLF предупреждения, без
  whitespace error).

## Review и остаточный риск

Независимый review: `PASS`. Единственный остаточный риск — hard crash между
созданием `O_EXCL` lock и `finally` может оставить lock-file. TTL/recovery для
такого crash-only случая не входит в согласованный scope и требует отдельной
задачи, если станет приоритетом.
