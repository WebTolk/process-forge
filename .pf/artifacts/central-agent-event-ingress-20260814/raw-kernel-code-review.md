# Raw Kernel Code Review

Дата: `2026-08-14`
Задача: `central-ingress-raw-kernel-code-review-20260814`
Проверенный файл: `tools/pf_runtime/raw_ingress_kernel.py`
Итог: `FAIL`

В текущем виде модуль полезен как черновой low-level primitive, но его нельзя считать безопасной базой для последующего host/service wiring. Главные причины: нарушение контракта каноникализации, незакрытое crash-window между raw append и индексами, и неполная recovery/API-семантика относительно зафиксированного idempotency/replay contract.

## Findings

1. **Критический дефект каноникализации: нестроковые ключи silently coercing в строки**. `tools/pf_runtime/raw_ingress_kernel.py:287-295`
`_normalise_json()` преобразует ключи mapping через `str(key)` вместо жёсткого отклонения. Это нарушает контракт canonical JSON для identity, допускает скрытые коллизии вроде `1` vs `"1"` и может менять смысл payload при хешировании.
`Исправление:` для объектов raw payload принимать только string keys; при любом non-string key выбрасывать `RawIngressError`. Нельзя silently normalise такой вход.

2. **Crash-window после raw append ломает dedupe/recovery semantics**. `tools/pf_runtime/raw_ingress_kernel.py:174-199`, `211-220`
Последовательность сейчас такая: append raw line -> потом write `raw_event_id` index -> потом write `native_identity` index. Если процесс падает после `_append_line()` и до записи индексов, повторная доставка того же события будет воспринята как новый first-seen event и запишет вторую raw line. Если падает между двумя индексами, можно потерять `native_identity` conflict detection для poisoned duplicate. Это прямо мешает требованию missing-only replay и безопасной dedupe после crash.
`Исправление:` нужен либо recovery path, восстанавливающий индексы из raw journal до приёма новых событий, либо staging/WAL protocol с crash-consistent transition state. Вариант “append first and hope index exists” для этого контракта недостаточен.

3. **Lock recovery не закрыта: stale lock после crash блокирует ingress**. `tools/pf_runtime/raw_ingress_kernel.py:132-156`
`_ExclusiveFileLock` создаёт lock-file через `O_EXCL`, но не проверяет ни liveness PID, ни lease age, ни owner metadata для safe recovery. При аварийном завершении `.ingress.lock` или shard `.lock` могут остаться навсегда; дальше код только ждёт timeout и падает. Это не просто operational inconvenience, а реальное ограничение на безопасный recovery.
`Исправление:` добавить lease metadata (`pid`, `created_at`, hostname/process marker), stale-lock policy и безопасный takeover/reap protocol; минимум документировать явный recovery hook, а не только timeout.

4. **Quarantine path смешивает разные классы ошибок в один `errors/poisoned/` каталог**. `tools/pf_runtime/raw_ingress_kernel.py:250-252`
Контракт различает `native_id_payload_conflict` и `raw_event_id_hash_collision` как разные классы инцидентов, но `_quarantine()` всегда пишет в `errors/poisoned/`. Для collision это неверная классификация и ухудшает разбор инцидентов.
`Исправление:` маршрутизировать quarantine path по коду ошибки: как минимум `errors/poisoned/` и `errors/collisions/`.

5. **Receipt/API пока не соответствует ожидаемому контракту для дальнейшего wiring**. `tools/pf_runtime/raw_ingress_kernel.py:45-52`, `179-181`, `199`, `253`
`RawReceipt` не содержит `normalized_event_ids`, `chat_message_ids` и не может выразить результат missing-only derived repair. Для минимального raw-only primitive это терпимо, но для безопасного host/service wiring этого API недостаточно: верхние слои не смогут единообразно обрабатывать duplicate/replay completion.
`Исправление:` либо расширить `RawReceipt` до contract-shape, либо явно зафиксировать transitional API и запретить считать его финальным ingress receipt.

6. **Нет pre-receipt проверки размера payload**. `tools/pf_runtime/raw_ingress_kernel.py:278-284`
Контракт требует reject malformed/oversized payload до выдачи raw id и до durable receipt. Сейчас `_validate()` проверяет только object-shape и сериализуемость. Ограничение размера отсутствует полностью.
`Исправление:` добавить конфигурируемый payload size limit и reject до `raw_payload_hash()`/`raw_event_id()`/append.

7. **`atomic_write_json()` не доводит durability rename до уровня parent directory**. `tools/pf_runtime/raw_ingress_kernel.py:114-129`
Файл temp fsync-ится, потом делается `os.replace()`, но родительская директория не fsync-ится. Это означает, что при жёстком power-loss durability индекса/чекпойнта после rename не гарантирована полностью. Для обычного “best effort atomic replace” код нормальный, но для заявленной durable storage semantics это ограничение надо считать открытым.
`Исправление:` где платформа позволяет, fsync parent directory после `os.replace()`; иначе явно зафиксировать это как platform limitation и покрыть recovery rebuild.

## Что подтверждено

- `canonical_json()` в остальном следует нужной схеме: UTF-8, sorted keys, compact separators, `allow_nan=False`, NFC для строк. `tools/pf_runtime/raw_ingress_kernel.py:55-60`
- `raw_event_id()` корректно исключает receipt/transport metadata через identity document, а `stable_native_identity_key()` правильно отделяет conflict-detection key от payload hash. `tools/pf_runtime/raw_ingress_kernel.py:67-80`, `256-275`
- Path containment реализован аккуратно и реально ограничивает runtime paths корнем storage. `tools/pf_runtime/raw_ingress_kernel.py:104-111`
- Используются межпроцессные file locks, а не только in-process mutex, что соответствует направлению контракта. `tools/pf_runtime/raw_ingress_kernel.py:132-156`
- Синтаксис модуля валиден: локальная проверка `compile(...)` прошла.

## Финальное решение

`FAIL` для использования как безопасной основы перед host/service wiring.

Модуль можно оставить как экспериментальный raw-storage primitive, но перед интеграцией обязательны минимум такие правки:

1. Запретить non-string keys в canonicalization.
2. Закрыть crash-consistency между raw journal и обоими индексами.
3. Добавить stale-lock recovery policy.
4. Развести quarantine storage по типам конфликтов.
5. Довести `RawReceipt` до contract-compatible формы или явно зафиксировать transitional boundary.
6. Добавить payload size guard.
7. Усилить durability story для atomic index/checkpoint writes или обеспечить rebuild-on-start.

Пока эти пункты не закрыты, ответ на вопрос “может ли minimal kernel безопасно предшествовать host/service wiring” — **нет**.
