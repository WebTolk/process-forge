# Реализация нормального PF Runtime daemon lifecycle

Status: ready_for_review

## Что упрощено

Lifecycle больше не выводится отдельными эвристиками в `start`, `stop`, cleanup и child singleton acquisition. В `tools/pf_runtime/service.py` добавлена единая `inspect_lifecycle()`.

Каждый daemon создаёт случайный неизменяемый `instance_id`. Он записывается одновременно в `runtime.lock` и `service.json`; lifecycle считается принадлежащим Runtime только при совпадении `instance_id`, PID и service state.

## Поведение

- `ready`: matching live instance и успешный `/readyz`.
- `starting`: matching live instance без готовности; повторный `start` ждёт его, не порождая второй daemon.
- `stopping`/`failed`: matching live instance требует корректного stop/recovery, а не удаления lock.
- `stale`: отсутствует matching identity, PID мёртв либо записи старого формата/несогласованы; cleanup может освободить их.
- `stop`: graceful HTTP shutdown только для `ready`; до endpoint publication и при managed failed state процесс завершается только после проверки matching instance и подтверждения exit.
- `serve`: публикует `failed` перед освобождением lock при исключении; lock освобождается только владельцем того же `instance_id`.

## Удалённые incidental rules

- PID без instance identity больше не считается singleton ownership.
- `stopped` больше не используется как неявное подтверждение нового start; нормальный stop освобождает lock.
- stale live PID с legacy/missing identity не блокирует recovery.
- stop не сообщает ложный успех, если managed PID не завершился к timeout.

## Проверки

`smoke_long_lived_runtime.py` дополнен проверкой matching `instance_id` у ready daemon; он сохраняет проверки двух concurrent starts, stop до endpoint publication, stale dead PID и stale live PID/reused PID.

- `python -m py_compile tools/pf_runtime/service.py tools/smoke_long_lived_runtime.py` — pass.
- `python tools/smoke_long_lived_runtime.py` — pass.
- `python tools/smoke_runtime_host_poc.py` — pass.
- targeted `release-test` (`smoke_runtime_host_poc`, `smoke_long_lived_runtime`) — pass, 55.84 s.
- schema validation и `git diff --check` — pass.

## Boundary

Изменён только транспортный daemon lifecycle. Agent Ledger, Project Router, Director, Inspector и PF Core business logic не стали Runtime-owned state.
