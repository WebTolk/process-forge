# Аудит жизненного цикла PF Runtime daemon

Status: ready_for_implementation

## Фактический путь

`runtime start` проверяет `service.json`, отдельно пытается восстановить stale state и запускает `runtime serve` в detached-процессе. Уже дочерний процесс создаёт `runtime.lock`, записывает `starting` service state, открывает HTTP-сервер и публикует endpoint. `stop`, `status`, `doctor` и IPC снова по-разному читают service state, lock, PID и `/readyz`.

## Лишняя сложность

1. `active_service`, `singleton_starting_pid`, `cleanup_stale_runtime`, `acquire_singleton`, `start` и `stop` имеют пересекающиеся правила определения жизни процесса.
2. Lock содержит только PID, а service state — отдельный PID/status/endpoint. PID сам по себе не доказывает, что это тот же Runtime: возможны stale record и reuse.
3. `stopped` используется как подсказка для стартового окна, хотя корректно остановленный daemon уже должен освободить lock.
4. `stop` вынужден угадывать, является ли отсутствие endpoint коротким запуском, зависанием или stale record.

## Целевая модель

Один runtime instance создаётся дочерним daemon-процессом и получает неизменяемый `instance_id`.

```text
lock(instance_id, pid)  ─┐
                         ├─ authoritative lifecycle inspection
service(instance_id, pid, state, endpoint) ─┘
```

Допустимые состояния: `starting`, `ready`, `stopping`, `stopped`, `failed`, `stale`.

- Совпадающие живой lock и service `instance_id` означают только `starting`, `ready`, `stopping` или управляемо неготовый/failed instance.
- Отсутствующий или несовпадающий `instance_id`, мёртвый PID, либо неполная старая запись — stale и может быть очищена.
- `start` не удаляет valid live instance: ждёт `starting`, возвращает existing `ready`, отказывает на hung/failed live instance.
- `stop` использует HTTP только для `ready`; valid live `starting`/unready instance останавливается как принадлежащий этому lock, затем подтверждает exit.
- Только daemon создаёт/освобождает свой lock. Parent launcher не владеет жизненным циклом и не создаёт параллельный источник истины.

## Инварианты тестов

1. Два start не запускают два daemon-процесса.
2. `starting` с совпадающим `instance_id` сохраняется и ожидается.
3. `stop` работает до endpoint publication.
4. Старые/incomplete lock records и PID reuse не блокируют recovery.
5. `ready` требует живой PID, matching instance identity и `/readyz`.
6. Успешный stop подтверждает exit; timeout — явная ошибка, а не ложный `stopped`.

## Граница

Это транспортный lifecycle PF Runtime. Agent Ledger, Director, Inspector, Router и project state не меняются и не получают runtime-дубликатов.
