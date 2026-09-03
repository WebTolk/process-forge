# Исправление timeout статуса Runtime

## Воспроизведение

После реального обновления `D:\.agents\processforge` до 1.2.1 процесс Runtime был `ready`, doctor проходил проверки lock, token, protocol и core version, однако `pf runtime status` возвращал `health=degraded` с `last_status_error.error=timed out`.

Первичная гипотеза о недостаточном двухсекундном deadline оказалась неполной. Под активным scheduler `/status` иногда не отвечал и за 10 секунд: scheduler держал общий `host.STATE_LOCK` во время инспекции и пересборки projection, а status повторно запускал reconciliation через `host.status_payload` и ждал тот же lock.

После устранения lock contention второй замер локализовал оставшуюся задержку: `last_event()` перечитывал целиком `.pf/runtime/events/events.ndjson`. На реальном журнале размером около 1,6 МБ один вызов занимал примерно 18 секунд.

## Исправление

- HTTP status теперь читает сохранённый runtime cache и Agent Ledger без повторного reconciliation;
- scheduler остаётся единственным владельцем тяжёлого reconciliation-пути;
- последнее событие читается с конца NDJSON-журнала блоками, без полного прохода;
- HTTP deadlines не увеличены и по-прежнему выявляют реально зависший Runtime;
- `tools/smoke_runtime_status_timeout.py` удерживает scheduler lock 2,2 секунды и проверяет быстрый поиск последнего валидного события в журнале из 50 000 строк.

## Критерий

Исправление считается принятым после focused smoke, существующих Runtime smoke-тестов, пересборки архива 1.2.1 и повторной проверки реального фонового Runtime.

## Проверка

- `smoke_runtime_status_timeout.py`: PASS;
- `smoke_runtime_status_version_truth.py`: PASS;
- `smoke_long_lived_runtime.py`: PASS;
- исправленный candidate commit: `59b286c462a9c9f7744c01ab6c4c4299935bbb21`;
- архив: 892 файла, SHA-256 `4093c1e6a9fe267cb86a7f232cc6b9a05967d5e12b5a3f97a2ed0c63910f6572`;
- archive structural/hash test: PASS;
- реальная установка повторно обновлена тем же target-side апдейтером 1.2.1;
- четыре последовательных `runtime status` под активным scheduler: `status=ready`, `health=ready`, один известный проект, 31 сессия Agent Ledger, без `last_status_error`.

Результат: PASS.
