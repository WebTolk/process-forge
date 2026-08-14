# Краткий аудит кодовой базы

Дата: 2026-08-14

## Объём и доказательства

Три независимых PF shell-workers с `gpt-5.3-codex-spark` работали только на
чтение и завершились штатно с durable `exit.json`:

- `runtime-observation-report.md` — Runtime, worker lifecycle, hooks/MCP;
- `process-contracts-report.md` — processes, schemas, templates и CLI;
- `quality-public-surface-report.md` — quality/release/public surface.

Базовые gates в основном checkout: schema validation, public cleanliness,
`codex-exec` driver validation, Python compilation, `release-check` и
`git diff --check` — PASS. Последняя команда выдала только предупреждения о
будущем LF→CRLF, не whitespace error.

## Подтверждённые находки

### Высокая: повторный `worker-run start` не защищён от уже running задачи

`command_worker_run_start()` всегда снова вызывает `prepare_worker_run()` до
проверки durable agent-run state. Поэтому повторный `worker-run start --detach`
для того же `task` способен создать второй PID и перезаписать наблюдаемое
состояние первого процесса. Это подтверждено статическим code path в
`tools/processforge.py`; текущие smoke не проверяют эту идемпотентность.

Требуемое исправление: до prepare атомарно отклонять status `running` (либо
ввести явный безопасный retry/replace protocol), а затем добавить regression
smoke с двумя последовательными start.

### Низкая: `worker-run start --wait` — инертный флаг

Парсер объявляет `--wait`, но implementation использует только `--detach`.
Пользовательский результат сейчас не нарушен: ожидание и так default без
`--detach`. Это CLI debt и риск будущей неоднозначности, а не функциональная
поломка.

Требуемое исправление: удалить `--wait` или явно сделать его конфликтующим с
`--detach` и покрыть parser test.

## Риски, не являющиеся подтверждёнными дефектами

- Публичные проверки запускаются отдельным `release-test --public`; простой
  `release-check` намеренно их не включает. Это становится риском только если
  CI публичного релиза вызывает лишь `release-check`. CI-конфигурация в этот
  короткий аудит не входила.
- `process-forge.local.yaml` разрешён в `examples/` и `templates/`. Это может
  быть осознанной поддержкой фикстур; доказательства утечки отсутствуют. Нужен
  лишь явный policy/test на допустимые fixture-варианты.
- Process/schema/template audit не выявил подтверждённых противоречий.

## Вне scope

Ни продуктовый код, ни Runtime lifecycle не менялись. Этот отчёт — основание
для отдельной remediation-задачи, если она будет запрошена.
