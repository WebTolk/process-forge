# Хранение исполнений и границы authority

Неизменяемые DTO находятся в `processforge_core.executions.model`, синхронный
Protocol `ExecutionRepository` — в `executions.ports`. Импорт и конструирование
не выполняют I/O и не создают backend. Repository, service, наблюдение ОС,
миграция и композиция адаптеров относятся к отдельным слоям. Этот срез DTO сам
по себе не включает SQL route и не доказывает интеграционную приёмку Runtime.

## Идентичность и валидация

`ExecutionKey(project_id, run_id, task_id, attempt)` обозначает попытку
существующего назначения; `task_id` равен assignment ID, новой сущности нет.
Непустые UTF-8 идентификаторы без NUL сохраняются точно: регистр, пробелы вокруг
непустого значения и форма Unicode не меняются. Пустые и состоящие только из
пробельных символов строки отвергаются. Нет повторной нормализации, идентичности
из пути или замены ID. Проверка допустимости filesystem selectors остаётся у
вызывающего слоя. Attempt — точный int >= 1; bool отвергается.

DTO — frozen dataclasses. Revision >= 1, generation >= 0,
`0 <= projected_revision <= revision`. Process identity содержит host,
необязательный boot, положительный PID, непрозрачный birth ID и необязательный
owned-tree ID. Проверка формы не доказывает существование процесса или отсутствие
его дерева.

Payload — JSON object без повторных ключей, нечисловых/бесконечных чисел, NUL
и строк, непредставимых в UTF-8. Модель сохраняет исходный текст и unknown fields.
Адаптер проверяет compatibility schema и канонизирует transaction payload:
sorted keys, compact separators, UTF-8, `ensure_ascii=False`, `allow_nan=False`.
Конструктор не проверяет подлинность receipt или соответствие checksum исходным
байтам, которых в DTO нет. Timestamp наблюдения требует явного UTC offset;
launch/store ID имеют форму UUID hex, checksum — `sha256:` и 64 строчных hex-цифры.

## Независимые владельцы

| Факты | Источник authority |
| --- | --- |
| Стадии Run и Assignment | Существующий Work YAML |
| Capsules, prepared inputs, содержательные artifacts | Неизменяемые файлы |
| Интерпретированные execution facts после явного cutover | Project SQL |
| Process/heartbeat/exit receipts | Evidence, допускаемое по exact launch identity |
| `status.json` после cutover | Производная compatibility projection |
| Владение сессиями Ledger | Существующий Agent Ledger |

Legacy events/hooks/accounting сохраняют прежние stores и ID. Search остаётся
отдельной производной БД; будущий workplace main store не активируется. Это
переходная топология, а не завершённая консолидация.

## Физическая активность, outcome и collection

Внутренние фазы: prepared, starting, running, stopping, unresolved, absent.
Current snapshot содержит только starting/running/stopping/unresolved.
Prepared attempt не создаёт current row. Reservation коммитится до создания
процесса. Смерть контроллера сохраняет unresolved ownership; TTL не доказывает
освобождение. Запрос stop и успешный сигнал не доказывают физическое отсутствие.
Повторное использование PID, запрет OS inspection, недоказанное отсутствие
потомков или нехватка evidence сохраняют unknown activity.

Доказанное отсутствие полного дерева атомарно связывает outcome с монотонным
history sequence и удаляет current ownership. Внутренние outcomes: completed,
failed, timed_out, cancelled, unknown_exit, lost, blocked. Они не добавляют
публичных status enum values: в частности, unknown_exit отображается адаптером
в существующий внешний статус. Public payload schema остаётся версии 1;
launch token, revision и generation не добавляются в публичный status.

Collection независимо принимает pending/collected/failed/refused. Ошибка сбора
не возрождает процесс, semantic refusal не означает принятие результата.
Поздний receipt/collection не меняет порядок history. Evidence старой попытки
может менять только её точный key; load_latest не выбирает цель такой мутации.

## Repository и гарантии чтения

Мутации сравнивают generation и expected revision. Receipt допускается по exact
key, launch token, kind, sequence и checksum: уже принятое идентичное evidence —
no-op, тот же sequence с другим содержимым — конфликт, меньший sequence — stale
no-op. Birth identity прикреплённого процесса неизменяема. Domain ports не
принимают SQL session, CLI object или filesystem path. Транзакция не охватывает
spawn, сигналы, wait, чтение output, backup, сканирование или projection I/O.

`current(limit=128, deadline=None)` читает readiness и только индексированные
current rows в одном snapshot. Limit — 1..1000. Переполнение, unknown coverage,
отсутствующая/неподдержанная БД и истёкший deadline не превращают неполный пустой
результат в доказательство нулевой активности. Deadline — absolute monotonic.
Guard не сканирует history, не читает terminal receipts, не reconciles и не
посылает сигналы. History pages используют монотонный sequence, закреплённый
high water и default limit 256; `after=None` означает конец страниц.
Projection ack выполняет CAS latest key/revision/generation без увеличения
lifecycle revision.

## Routing и восстановление

До opt-in unbound project сохраняет legacy route. Чтение и конструирование
ничего не создают. При binding проверяются exact project/store identity,
namespace и SQL readiness. Отсутствующая, чужая, повреждённая или частичная БД
блокирует работу без fallback в JSON. Binding закрепляет маршрут; authority и
readiness устанавливает только SQL transaction. Нужен явный project ID;
имя каталога не заменяет его при initialization/migration.

Миграция требует явного offline maintenance, исключения старых writers,
доказанного quiescence, стабильных sources, проверенного backup и checkpointed
import. Live takeover не поддерживается. Pending binding блокирует capable
writers. History может быть неполной, но первый cutover требует complete active
coverage. После cutover выполняется roll-forward из SQL и ремонт производных
projections; JSON не импортируется повторно как новая истина. Старые binaries
не умеют соблюдать новый marker и не поддерживаются как writers после cutover.
Fresh SQL route разрешён только при успешном явном создании нового project root;
существующий root, включая forced initialization, не становится fresh автоматически.
