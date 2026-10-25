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
| Канонические knowledge и file resources | Существующие файлы |
| Capsules, prepared inputs, содержательные artifacts | Неизменяемые файлы |
| Интерпретированные execution facts после committed SQL cutover | Project SQL |
| Process/heartbeat/exit receipts | Evidence, допускаемое по exact launch identity |
| `status.json` после cutover | Производная compatibility projection |
| Владение сессиями Ledger | Существующий Agent Ledger |

Legacy events/hooks/accounting/search сохраняют распознанные пути, domain
application IDs, domain versions и данные. Search остаётся отдельной производной
БД. Добавление UUID metadata в распознанные legacy stores отличается от PF main
envelope и execution JSON import: оно не переносит domain rows и не включает SQL
execution authority. Будущий workplace main store не активируется. Топология
остаётся переходной; другие драйверы, RAG, scheduler и полная консолидация legacy
domains не входят в этот контракт.

`pf_store_meta` сохраняет UUID/scope/stable owner identity, `pf_schema_versions` —
code-owned namespaces, версии и checksums. Legacy adoption регистрирует только
`store_identity@1`, сохраняя квалифицированные domain schemas, constraints и FTS
objects. Main использует собственный envelope с `execution@1` и
`execution_migration@1`. Legacy identity pins и execution binding закрепляют
точные targets; у execution main нет дублирующего legacy identity pin. UUID
metadata сама не выдаёт доступ и не заменяет domain validation. Чужие,
повреждённые, будущие, изменённые или конфликтующие stores отвергаются без
переименования формата или обхода через rebuild.

## Конфигурация и неизменяемые снимки

Один native `ConfigurationProvider`, привязанный к точному контексту, предоставляет
полный application `PFConfig` для CLI, standalone Core, MCP/Runtime/hooks, workers
и maintenance. Для разрешённых ключей порядок: builtin -> device -> явно
сохранённые поля выбранного workplace -> project -> authorized context. Presence
берётся из того же валидированного чтения YAML; явно заданные false/default
перекрывают базу, отсутствующие workplace keys наследуют device. Project/context
используют typed allowlist `ProjectPFConfig` и null-inherit. Они не меняют locked
policy или поля вне allowlist. Конфигурация не выдаёт filesystem, SQL,
инфраструктурные права или доступ к телам model-visible inputs.

Device source содержит полный PFConfig, а не driver-only global reader.
`database.driver` следует тому же merge; SQLite — operational default при
отсутствии selector и единственный реализованный драйвер. Отсутствующая
конфигурация не требует нового файла или сериализации секции `database`.
Profiles остаются отдельным валидированным механизмом targets: collisions и
нарушение scope отвергаются; refresh не переключает bound store UUID/path.
Объявленный device path выбирается один раз на command/session без disk scan
или CWD discovery. Provider и CRUD описаны в
[Runtime configuration](runtime-configuration.md).

Host получает один явный snapshot на operation и передаёт pinned provider
downstream. Refresh влияет только на следующие операции; существующий snapshot
не меняется. Mutable global current-project config отсутствует. Cold construction
ничего не читает и не инициализирует. Pure reads не создают config, DB или
maintenance files. Первый invalid input даёт ошибку; later invalid reload
сохраняет last-valid source вместе с presence и diagnostics по прежним правилам.

Новый native launch передаёт private attempt-local `configuration.snapshot.json`,
закреплённый до spawn и проверяемый по exact authorized path, hash, attempt
identity, размеру <= 65536 bytes и strict PFConfig shape. Wrapper передаёт тот же pointer/hash
дочернему процессу без чтения live config посреди attempt. Sidecar не является
policy, prompt input, публичным status field или изменением capsule. Его native
scope должен быть явно выдан; нехватка прав блокирует dependent launch.
Уже работающие legacy wrappers сохраняют прежний route. Standalone wrapper без
pinned transport может использовать provider только при собственном разрешённом
read scope. Metadata-only visibility не разрешает чтение тела.

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

SQL heads/current/history sequence, launch tokens, process identity, receipt
admissions и projection ack остаются отдельными фактами с разными ролями.
Под существующим task lifecycle lock projection публикует последний authoritative
compatibility DTO через atomic replace `status.json`, затем выполняет CAS ack.
Сбой оставляет head dirty для indexed/exact-task repair; старая попытка не
перезаписывает latest projection. CLI/MCP/continuation после cutover читают SQL,
даже если projection устарела.

## Admission и ограниченное наблюдение

Capable spawn paths берут workplace admission при enrollment, затем project
admission, existing task lifecycle lock и SQL transaction. Reservation коммитится
до spawn; SQL transaction не охватывает создание процесса. Shutdown и registration
используют тот же admission protocol и durable Runtime stopping fence. Unknown
routing/ownership/tree state или gate timeout сохраняет unknown activity; TTL и
PID-only probes не доказывают idle. Enrolled project не обходит недоступный
workplace gate, объявляя себя standalone. Guard с бюджетом 500 ms только наблюдает
ограниченное current state: без migration, backup или history scan. Acceptance
400000 history с zero-terminal reads относится к SQL-ready operation; legacy
projects сохраняют прежний bounded observer. File-only operation не требует
bootstrap Runtime/MCP, network или LLM.

## Routing и восстановление native migration

Страница описывает принятый итоговый контракт. Она не утверждает, что текущий
живой проект мигрирован или интеграционная QA реализации уже пройдена.

Обычный поддержанный update и первая безопасная запись автоматически вызывают
native migration script/service без project opt-in, ручного переноса данных или
agent/LLM/model-provider calls. `tools/migrate-storage.py` — native entrypoint для
inspection, apply и recovery; update вызывает квалифицированный установленный
код, first-write использует тот же coordinator для standalone/file-only.
Успешная установка сама не означает project readiness. Pure status/config/doctor/
guard reads не запускают migration или scans.

До публикации pending pin/binding распознанный unbound legacy project сохраняет
прежний route. Active/unknown ownership откладывает migration с diagnostics;
поддержанные start/stop/collect, IDs и receipts активных attempts сохраняются.
Retry происходит после terminal reconciliation/collection или при следующем
mutating use, после освобождения lifecycle/target locks и SQL sessions. Нет
scheduler, polling loop, live takeover или automatic kill. Отсутствующий explicit
stable project/owner ID, ambiguous source или unknown old writer нельзя объявить
безопасными через config или opt-in flag.

Proven safety — host evidence для exact authorized project/store, target и
generation: quiescence, отсутствие pre-spawn gap и живого owned tree, стабильные
sources и квалифицированное исключение старых writers. Проверка повторяется под
admission при freeze, resume и непосредственно перед cutover. Empty registry,
текущая версия, terminal string, истёкший TTL, PID probe или один
`offline_confirmed` не являются proof. Отсутствующее, устаревшее, изменённое или
недоступное proof не разрешает migration/cutover; до pending сохраняется
описанный legacy route. Старые binaries технически не
соблюдают незнакомые markers; их исключают реальным ownership/maintenance
evidence, а после SQL cutover они не поддерживаются как writers.

При proven safety exact pending identity pin/execution binding публикуется до
DB mutation. Capable clients блокируют обычный доступ к pending target и
разрешают только восстановление точного плана. Missing/partial bound storage
не допускает fallback в JSON или другой target. Ready access проверяет exact
project/store UUID, scope/owner, pinned path, schema/checksum и readiness.
Binding задаёт route и identity pin; только SQL transaction устанавливает
execution authority/readiness. Нужен explicit manifest project ID; имя каталога
или молча созданный replacement owner ID его не заменяют.

Migration сохраняет deterministic descriptors, frozen source manifests/original
bytes, verified WAL-aware backups, journals и same-batch checkpoints. UUID
adoption добавляет metadata на месте без изменения domain rows/IDs; per-target
commit отделён от execution import и global file journal. Unused absent stores
не создаются ради abstraction. Execution import использует только наблюдаемые
latest snapshots без выдумывания перезаписанной history; имена attempt directories
определяют только allocation floors. Batch не превышает 256, import и checkpoint
коммитятся в одной transaction. History может быть неполной, но первый cutover
требует zero proven current executions и complete active coverage. Нельзя
пропускать invalid records, скрывая unknown active work.

Единственный execution cutover — CAS commit `execution_state` из importing/legacy
в ready/sql с target generation вместе с ready marker `execution_migrations`.
UUID adoption сама не является этим commit. Proven-safe migration синхронно
завершается до продолжения initiating write; interruption сохраняет pending/
checkpoint для automatic exact resume при следующем mutating use. Resume
проверяет code/descriptor/source facts, тот же backup и checkpoint без повторного
mint UUID или произвольного второго backup. Ready target не откатывается
неявно, если следующий target завершился ошибкой.

После cutover recovery выполняет roll-forward из SQL и ремонтирует только owned
projections/reports; JSON не импортируется как новая истина. Automatic abort
отсутствует. Explicit pre-cutover abort требует admission, неизменных sources и
proof отсутствия ready authority/new SQL commits. Restore выполняется в новый
target с controlled offline binding switch; old-Core rollback после SQL writes
требует отдельно квалифицированного reverse export. Maintenance inspection и
существующие `journal-maintenance` execution inspection/import/resume interfaces
служат диагностике и управляемому ремонту, не являются условием обычной migration
для пользователя. См. [SQLite journal maintenance](sqlite-journal-maintenance.md).

Fresh SQL route разрешён только при успешной explicit initialization нового
flow root. Существующий root, включая forced initialization, не становится fresh
по предположению. Публикация fresh binding/DB recoverable, но не atomic между
files и SQL. Fresh marker в состоянии pending закрывает legacy route сразу после
публикации, даже если binding ещё отсутствует. Чтение сообщает о pending без
ремонта. Безопасная обычная mutation или native resume восстанавливает только
закреплённые marker owner/UUID/profile под admission, после проверки native
capability и стабильной safety generation. Перед ready safety проверяется снова;
выбор другого target или нового UUID запрещён.

????? ????????? adoption ????????? ????????? retirement commitment, ???????? ?
filesystem identities, successor generation ? committed native epoch. ?????????
??????? ????????? durable state ?? Core capture ? ?????????? ??????????? ????????
OS lease; ???????? manager ????? bound ????? ???????????. ?? bound ??? ??? ?????
???????? ???????? ??????? owner/tree closure: ????? ?????? ????????? ?? ?? ????????.
Pending/updating head ????????? shared entry, ??????? ???? ?? ????? epoch.
Migration proof ????????????? ????????? owner/routing/instance/targets ? ??????
pinned PFConfig ??? admission. Native update ????????? ?????? pending transition
?? overwrite, ????? successor epoch/head. Maintenance ????????? ?????? ??????
child ? ??????????? lease; ?????????? child ???? ?? publication ?? ?????????
????????? ??????????.


### ?????? cold-???????

??? ???????????? ????????? ??? ????????? ??????? ingress owner ????????? ???????? ????????????????? ??????????? cold-???????. ???????? native controller ????????? ?????????? ?????? ?? retirement, ???????? ?????? ???????? frozen publication ? ??????????? backup ? ????????? ????????? adoption `cold-v1`. ????? bound ??????? ???????? ?????????? ???????? ??????????? native leases; ?????????? controller/service ?? ?????????.

Private fixed native-maintenance descriptor ???? ???????? ?????????????? checkpoint: prepared-resource adapter ??? ?? ???????? ????????? runtime/deployment grants. ?? ?????????? ????? ??????, ???????? ?????????????? ???????? ? ???????? ???????????? ?????????, principals, boot ? fault-????????? ??? ?????? ??????? ??????? ?????????? deployment. Caller flag, receipt, ??????????? ??? interpreter ??? ????? ?????? Job ?? ?????????? retirement.
