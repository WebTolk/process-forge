# Подготовленный вход исполнителя

Строгий egress-контекст v2 обрабатывает [управляемый брокер](egress-engine.md).
Native-подготовка возвращает `enforcement_unavailable` до копирования исходных
данных в запрос исполнителя. Подготовка существующих контекстов v1 не меняется.

Подготовленный вход — ограниченный приватный пакет данных для одного проверенного контекста назначения и одной попытки. ProcessForge формирует его из действующего контракта исполнения, закреплённых капсулы и снимка, обязательных источников, выходных файлов и текущих разрешённых ресурсов. Он не создаёт новую Work и не позволяет исполнителю выбрать более новый процесс, этап, источник или набор прав.

Формат версии 1 описан в [`prepared-input.schema.json`](../../../schemas/prepared-input.schema.json). Манифест хранится в приватном каталоге выполнения для попытки: `attempts/<attempt>/prepared-input.json`; в команде и состоянии запуска сохраняются относительный путь внутри проекта и контрольная сумма `sha256:`. Верхнеуровневый `project_root` — приватные служебные метаданные. Не переносите его и разрешённые пути Workplace в публичные артефакты.

## Содержимое манифеста

Манифест содержит `kind: pf.prepared-input`, `visibility: private_runtime`, идентификаторы проекта, Run, Assignment, контекста и попытки, полный раздел `input`, его контрольную сумму, исходное состояние выходных файлов и фиксированные ограничения размера JSON и встроенного содержимого. В `input` входят цель, путь к капсуле и хеши её байтов, контракта и намерения, закреплённые снимок и процесс, текущее представление этапа, явная область действий и файлов, обязательные выходы и отчёт, источники, необходимые возможности, параметры, правила делегирования и разрешённые ресурсы.

Для каждой попытки манифест создаётся один раз. Максимальный размер JSON в UTF-8 — 4 МиБ. Включается не более 64 КиБ начала одного текстового файла и не более 256 КиБ суммарно. Для слишком больших или нетекстовых источников остаются проверенная относительная ссылка на файл и контрольные суммы; ProcessForge не копирует дерево исходников в инструкции. Перед передачей проверяются объявленная контрольная сумма и область чтения. Большой источник всё равно требует действительной ссылки и разрешения исполнителю на чтение.

Атомарная публикация использует записанный и синхронизированный временный файл и создание жёсткой ссылки в том же каталоге без перезаписи. Файловая система каталога выполнения должна поддерживать жёсткие ссылки. Иначе операция явно завершается ошибкой, не оставляя неполный итоговый манифест.

Проверка материалов T02 имеет отдельные фиксированные пределы: 64 ресурса, 2 048 файлов и 32 МиБ суммарно; 20 000 просмотренных элементов; 256 файлов и 8 МиБ на ресурс; 1 000 000 байт на файл; 2 048 созданных документов и 32 МиБ поискового содержимого. Эти ограничения относятся к проверке ресурсов и производным материалам, а не дают доступ к каталогу. Превышение может остановить подготовку до запуска worker.

Разрешение на ресурс с `metadata_only` содержит только навигационные метаданные без разрешённого пути к содержимому. Оно не даёт права читать тело ресурса или корневой каталог. Полнотекстовый ресурс проверяется относительно закреплённой привязки, текущего разрешения проекта и подмножества этапа; приватный манифест хранит переносимые ссылки, происхождение и ограниченные хеши файлов. Разрешения на шаблоны, инструменты и MCP также сверяются с закреплённым и текущим выбором и проверяются до запуска. Само наличие ресурса в реестре ничего не разрешает.

Явный tool grant закрепляет выбранный ID реестра. Публичный snapshot содержит
только переносимый `path_ref` (`registry: tools`, `id`) и
`definition_fingerprint`: SHA-256 полного авторитетного определения в UTF-8 JSON
с сортировкой ключей, компактными разделителями, сохранением Unicode и запретом
нефинитных чисел. Digest охватывает команду, приватные пути, статус и ограничения;
сами команды и приватные пути в snapshot не копируются. Prepare и start сверяют
закреплённый и текущий выбор, повторно читают единственную актуальную запись
реестра и отклоняют отзыв доступа или изменение записи даже без refresh.

Файловый tool сохраняет прежние проверки существования и границ пути.
Command-only tool получает `resolution.status: descriptor` с проверенным `entry`
и непустой командой только в приватном prepared input. Descriptor не даёт доступа
к каталогам или телам файлов и не добавляет широкого directory grant для Codex.
Templates и MCP сохраняют прежнюю файловую форму. Отсутствие ссылки или digest,
неоднозначная или изменённая identity, изменение определения и отзыв записи
означают отказ. Старые immutable snapshots/capsules не дополняются: новым tool
grants нужен свежий governed context.

## Передача драйверам и выполнение

Каждый подготовленный драйвер получает зарезервированные переменные окружения `PF_PREPARED_INPUT_FILE` и `PF_PREPARED_INPUT_SHA256`, а также `PF_WORKER_ATTEMPT`. Драйвер не может задавать эти значения сам. Схема `runtime-driver.schema.json` описывает необязательный флаг `prepared_lifecycle_wrapper` и закрепляет эти имена. Включение обёртки задаётся доверенной конфигурацией драйвера, а не полями события.

Ручная подготовка создаёт такой же манифест попытки и ссылку на инструкции, но не запускает процесс. Встроенный `generic-shell` включает `tools/prepared_executor.py`: оболочка проверяет путь, хеш исходных байтов, идентичность и размер манифеста до запуска прежней целевой команды с унаследованными `stdin/stdout/stderr`, рабочим каталогом и окружением. Она записывает `heartbeat` начала и периодические обновления, финальный статус и устойчивый `exit contract`. Оболочка не запускает PF или MCP и не заявляет об изоляции на уровне ОС.

Codex использует существующую оболочку `tools/codex_exec_worker.py` и получает тот же подготовленный манифест. Инструкции требуют проверить путь и контрольную сумму, использовать только встроенные данные и объявленные ссылки, не пересобирать контекст и не запускать другую Work, а для `metadata_only` обращаться лишь к метаданным. В подготовленном режиме Codex получает только постоянные инструкции и проверенный манифест: он не читает изменяемые инструкции исполнителя, текст capsule или указатель на файл доступа к рабочей области. Он также не получает широкие `--add-dir` из таких путей. Подготовленному исполнению через generic-shell не нужны соединение MCP или сеть; это не ограничивает действия программы, если их не сдерживает системная песочница.

Непосредственно перед запуском ProcessForge повторно читает манифест попытки и проверяет контрольную сумму, точную идентичность Work/assignment/context, привязки капсулы, fingerprint ввода, актуальные источники и разрешения. Изменённый источник, устаревший снимок, отозванное разрешение или несовпавший путь блокируют запуск. Манифест — запись о передаче данных, а не новый источник полномочий.

## Попытки, выходы и сбор результата

Каждый явный запуск подготовки получает новый каталог попытки; предыдущий манифест не перезаписывается. Сохраняется исходное состояние каждого обязательного выхода и отчёта: отсутствует либо присутствует с checksum, размером и временем изменения. Номер попытки увеличивается; после сбоя worker не переиспользует прежнюю попытку молча. Настройка `max_retries` задаёт допустимый предел, но автоматического цикла повторов нет. После `ready` команда `start` использует ту же подготовленную попытку и точно сохранённую команду. Изменение предпочтений требует явного `prepare`. Если запуск заблокирован, сначала устраните причину, затем выполните явный `prepare` перед новым `start`.

До создания неизменяемого контекста назначение исполнителя должно явно задавать `expected_report.artifact` и соответствующую область записи. Обычная Work основного процесса без объявленных выходов не готова к запуску исполнителя: возвращается `worker_report_undeclared`. ProcessForge не определяет полномочия по имени файла.

При сборе результата контекст попытки проверяется повторно; обязательные выходы, включая ожидаемый отчёт, должны существовать и относиться к этой попытке. До фиксации `receipt` отчёт проверяется на UTF-8 и ограничивается 2 МиБ; каждый выходной файл ограничен 8 МиБ, общий объём — 32 МиБ. Отчёт с неверным UTF-8 или превышением размера отклоняется без фиксации `receipt`: его можно исправить и повторить сбор для той же попытки. Файл, не изменившийся с момента исходного среза, не принимается как её результат. ProcessForge сохраняет `receipt` попытки с контрольными суммами выходных байтов. Повторный сбор с тем же `receipt` возвращает завершённый результат; изменённые байты отклоняются. Управляемый сбор сохраняет основной жизненный цикл; долговечные идентификаторы `receipt`/завершения и восстановление после потери владельца позволяют продолжить после прерывания без дублирования событий.

Автоматический supervisor отличает завершённый захват от нового сбора. Согласованная закрытая связка prepared input, capsule, receipt и completion попадает в `historical_observed` и `observed`, но не в `collected`. Наблюдение перечитывает ограниченные служебные документы; оно не перечитывает исходники и выходные файлы, не подтверждает текущий доступ, не принимает результат заново и не завершает основную Work. Такая попытка не требует ожидания сбора при остановке. Отсутствующий, несогласованный или недоступный служебный документ возвращает обычный путь сбора. Явный collect, первый захват и восстановление после прерывания сохраняют все описанные выше текущие проверки.

После первого полного сбора может сохраняться устойчивый смысловой отказ именно этой попытки. Распознаются `required_source_changed`, `prepared_input_changed`, `prepared_input_context_mismatch` и `work_context_mismatch`, возникшие непосредственно в существующих проверках prepared input. Произвольное исключение с таким же текстом, ошибки чтения и блокировок, неверный UTF-8 и неизвестные ошибки такую запись не создают. Private-файл `collect-block-<progress-key>.json` связан с точными байтами prepared input, identity, fingerprint входов и состоянием служебных документов захвата. Короткий ключ служит только поиску; весь документ должен совпасть. При каждом наблюдении метаданные перечитываются и проверяются. Изменение состояния захвата возвращает полное восстановление; новый устойчивый смысловой отказ при нём получает отдельное наблюдение. Несогласованное, отсутствующее или недоступное подтверждение возвращает полный сбор.

Пока требуется восстановление, supervisor выводит `recovery_required` с задачей, попыткой и причиной, включает задачу в `observed` и `failed` и возвращает ошибку. Полный сбор не повторяется, захват и завершение основной Work не утверждаются. Одного восстановления исходника недостаточно для автоматической приёмки: нужен явный `worker-run collect` либо новая подготовленная попытка. Явный collect всегда сохраняет полные текущие проверки. Успешный захват имеет приоритет перед прежним отказом; изменение receipt/completion также делает прежнее наблюдение неприменимым и возвращает полное восстановление после прерывания. Неудачный ручной повтор не доказывает устранение прежнего отказа. Final drain остаётся явно незавершённым с ошибкой, а не повторяет тот же полный сбор в цикле.

Это контракты исходного checkout. Приёмка установленного Core, Workplace и реального Host проходит отдельно в T06; локальные проверки схем и smoke-тесты не подтверждают поведение установленной версии.

См. [контекст Work](work-context.md), [чтение ресурсов Work](work-resources.md), [capsule контекста](context-capsule.md) и [драйверы выполнения](runtime-drivers.md).


### SQL lifecycle и совместимость prepared input

Для SQL-ready проекта attempt выделяется SQL до создания immutable input.
Неудачная подготовка сохраняет planned attempt; повторная явная подготовка
получает следующий номер. После записи input, prompt и captured paths приватный
CAS переводит planned в ready/manual_required. Номер не выводится из каталогов.

Перед Popen reservation фиксирует starting/current под workplace/project admission
и task lock. Native wrapper публикует process/heartbeat/exit evidence с точной
идентичностью attempt и checksum. Windows Job Object охватывает wrapper и его
потомков; Linux использует отдельную process group. Exit receipt, смерть одного
PID, таймаут и успешный сигнал сами по себе не доказывают отсутствие дерева.
Неопределённость сохраняет current. Stop intent фиксируется до сигнала.

Manual collection и отмена ready/manual до запуска не создают process, launch
или физическую историю. Collection receipt/completion marker и SQL collection
сверяются при повторе; отказ collection не возобновляет процесс. Status JSON
служит восстанавливаемой проекцией; после binding CLI читает SQL даже при старой
или недоступной проекции.

Старый immutable prepared input без native configuration grant остаётся без
sidecar body access. При capable wrapper native captured receipt paths могут
переноситься в каталог его attempt приватным CAS; сам input, его checksum и
scope не переписываются. Полная конфигурация закрепляется на время операции и
передаётся новому wrapper только через точный native grant.


### Private native-maintenance authority

Для фиксированного `native-maintenance-fixed-v1` Core producer проверяет один
явный dictionary request `workspace_access.tools[]` против единственного
актуального configured descriptor-only tool с capability
`processforge.native-maintenance.fixed-v1`. Его private policy:

```json
{"native_maintenance":{"schema_version":2,"profile":"native-maintenance-fixed-v1","bindings":["полные точные объекты request.native_maintenance"]}}
```

`bindings` содержит непустой ограниченный список объектов, без wildcard/default;
строка в примере обозначает место объекта и не является допустимым grant.
Запрос содержит `id`, точный tools `path_ref` и `native_maintenance` с полной
identity/attempt, canonical job digest, descriptor/runtime/execute-source pins,
operation, management/qualification pins и deployment (`null` для archive и
construct-management). Четыре штатные resource groups остаются прежними.
Authoritative policy сохраняется в `tools[].resolution.entry`, явный запрос —
в `resources.requested.tools[]`. `definition.command` не интерпретируется.

Полномочие выдаёт владелец trusted policy в пересечении со свежим Work issuer.
ID, command, descriptor path, metadata, PFConfig и hash сами полномочий не дают.
Обычные small role bodies, qualification и material manifest требуют собственных
required-source body declarations и exact read scope. Для archive/runtime members
дополнительно необходим явный material grant, описанный ниже. Runtime требует `body` и `execute`;
исполняются только четыре закреплённых роли wrapper/harness/controller/native.
Повторный независимый gate в harness проверяет binding до чтения role bodies;
management/qualification/deployment pins проверяются до compilation/import.

`native_launch.maintenance={runtime,job_sha256,material}` — производный immutable marker,
покрытый полным checksum. Policy/request входят в semantic input fingerprint.
Старые preparations и capsules не дополняются при start/collection. Строгая схема
объявляет только существующие optional configuration и maintenance markers;
неизвестные top-level и marker fields запрещены.

Archive qualification не требует deployment. Construct-management требует
собственного точного bundle `write_product` scope. Cold binding содержит
`access:[read,write,acl]`, одну operation, canonical deployment digest и management
pin; он не заменяет actual token/ACL, held fence, retirement, epoch и independent
leases. Текущие source budgets сохраняются: oversized closure блокируется.
Synthetic fixture qualification не является normal-host или genuine cold proof.

Windows mixed-slash harness argument исправлен в Core command builder только
для точного шаблонного аргумента private fixed profile: путь составляется
лексически с нативными разделителями. Строгие validator/wrapper и generic argv
сохранены; fixed-command acceptance, tamper и generic-path регрессии проходят.
Project-relative body reference и фактическое расположение исполняемого harness
проверяются независимо: source требует точных Work/tool/body grants и совпадения
байтов, а `capture_job` требует, чтобы импортированный harness находился именно
по закреплённому пути внутри management project. Совпадающий hash копии в другом
root этого условия не заменяет: отказ `harness_path_mismatch` сохраняется.
`management` отдельно связывает namespace project с prepared project root,
qualified runtime closure — с фактическим interpreter, а `validate_preparation`
сверяет четыре executable source roles с distribution перед fixed launch.
Произвольный внешний distribution не становится разрешённым через body reference.

Для normal fixture полный независимый distribution расположен в самом
management project, вне replacement targets. Он содержит Python Core/bootstrap/
tools и необходимые schemas/templates; inventory четырёх файлов, создаваемый
`construct_management`, такой distribution не заменяет. Fixture импортирует
реальный закреплённый harness и запускает producer в новом процессе с собственным
Core, без изменения `__file__` и без унаследованных cached modules. Настоящий
маршрут producer → prepare/schema/write_once → fixed start/wrapper/harness →
collection проверен вместе с before-effect отказами для неправильных origin,
body, management root, runtime origin и command tamper. Это проверка source route:
freshness, qualification и малая runtime closure остаются явно синтетическими.
Полная независимая operational qualification, фактическая пригодность большого
комплекта, доставка management distribution и genuine host/cold evidence требуют отдельных
разрешённых проверок; source completeness и deployment readiness из fixture
success не следуют. Budgets и публичные/generic контракты сохранены.


### Private native material и начало запуска

Текущая private policy/request/job revision — строго **2**; предыдущий alpha6
prototype не является поддерживаемым внутренним форматом. Старые, смешанные,
неизвестные версии и поля отвергаются. Capability/profile IDs и четыре resource
groups неизменны; released generic prepared input и configuration snapshot
сохраняют свой контракт. Для retry требуется новая явно выданная exact identity,
request/policy/capsule/attempt; start не дописывает прежний immutable документ.

`native_maintenance.material` одинаков в запросе и одном точном binding policy.
Он содержит `body_manifest`, два непересекающихся project-relative roots
`archive/runtime`, `permission=body-and-qualified-runtime-load`, точный каталог
capture фактической попытки и конечные quotas. Manifest — обычный явно выданный
body source. Его перечисление, metadata, ID или hash отдельно не дают доступа
к binaries. Issuer дополнительно выдаёт read каждого member и write_artifact
capture-prefix; deny имеет приоритет. Archive остаётся data-only. Runtime отдельно
требует body+execute, closure и независимо qualified первоначальный origin.

Producer проверяет весь конечный набор manifest members до native member IO.
Разрешены один archive, один interpreter и роли dll/stdlib/bootstrap; runtime
rows точно совпадают с management closure. Safe Windows handles удерживают
файлы и ancestors без reparse/alias/hardlink и write/delete sharing; actual
FileId/volume, size, mutation и SHA256 проверяются потоково. На неподдержанном
backend — отказ. Runtime не переносится; archive получает create-once snapshot.
Только полный успех публикует immutable index и receipt
`pf.native-material.available-body`. Receipt связывает полную identity, job,
manifest/request pins, index pin и checked totals. Старт не ремонтирует missing
receipt/index/snapshot, а collection не выдаёт дополнительных прав.

| Ограничение | Предел |
| --- | --- |
| Ordinary Work sources | 128 файлов, 1 МиБ на файл, 8 МиБ всего |
| Prepared JSON / inline file / inline total | 4 МиБ / 64 КиБ / 256 КиБ |
| Material manifest / index | по 1 МиБ |
| Material members / roots | 4096 / 2 |
| Material member / interpreter / aggregate | 128 МиБ / 32 МиБ / 512 МиБ |
| Capture chunk / working buffer / accounted metadata | 64 КиБ / 1 МиБ / 16 МиБ |
| Capture disk, включая snapshot/index/partial | 512 МиБ |
| Archive / expanded / member / entries | 128 МиБ / 256 МиБ / 32 МиБ / 4096 |
| ZIP central directory / header total / one header | 4 МиБ / 4 МиБ / 16 КиБ |
| Downstream payload ceiling | максимум 2 ГиБ, дополнительно exact issued budget |

Действует минимум применимых bounds. До downstream allocation/compile проверяется
консервативный peak по actual archive/expanded/manifest/leaf sizes против именно
выданного budget. Ceiling не означает unconditional allocation и не обещает общий
RSS/commit PF. До ZipFile/decompression проверяются bounded EOCD/central/local
headers, offsets, aliases, compression и expansion. Private archive использует
реальный raw embedded Core manifest, native parser, leaf seal и checksum inventory;
outer release sidecar его не заменяет. ZIP64/multidisk/encryption и посторонние
members отвергаются. Quotas не повышаются автоматически.

### Lifetime preflight и короткий admission

Оба настоящих start consumer, SQL и legacy, входят в Core
`native_start_preflight` **до** admission и task lifecycle lock. Core удерживает
actual handles на актуальные policy/registry, assignment/run/capsule/snapshots,
обычные body sources и configuration snapshot; затем повторяет штатную current
semantic-input проверку. Harness `hold_start_material` удерживает index, archive
snapshot, исходные runtime/material references и принятую native operation lease.
Все material body/hash/ZIP/reference/qualification checks заканчиваются вне gate.
Core один выдаёт operation-local preflight: это непереносимый объект в активном
контексте текущего process/thread, а не caller dict, receipt, hash или boolean.
Standalone harness удерживает material, но не выдаёт current-policy seal.

Внутри gate выполняются bounded проверки живого preflight, identity/current attempt,
неизменного command/reference, accepted native entry/lease, версии каталога run
для новой cancellation и локальной конфигурации. Private command ограничен 64 КиБ.
SQL сохраняет current-attempt/revision/generation CAS и reserve-before-spawn;
legacy под тем же lifecycle lock повторно читает current state и публикует starting
до spawn. Native path не делает material rehash/ZIP/history/Job scans внутри gate;
SQL observation после spawn вынесено за admission. Generic paths сохраняют прежний
порядок проверок и существующие admission/stop primitives.

Command handle освобождается после одноразового admission: запуск использует
проверенное значение команды из памяти, поэтому последующая запись command.json
не меняет argv/env. Остальные handles и lease живут до **синхронного завершения**
wrapper/harness; их освобождение и metadata checks также происходят за admission.
Private maintenance требует заранее подготовленную ready попытку и синхронный
start; detach для этого unreleased private profile отказывает, поскольку без
квалифицированной передачи held references освобождать parent нельзя. Обычные
released generic detach/file-only/config/legacy flows не меняются.

Wrapper и harness независимо проверяют immutable prepared checksum, body права,
origin, identity/attempt и pins. Сам consumer `execute` удерживает свои references
на время compilation/effects. OS namespace/ancestor ACL, initial trusted bootstrap,
independent leases/epoch и genuine fence/retirement по-прежнему являются отдельными
условиями. Потеря parent или его token не становится доказательством platform trust;
parent/child crash и реальный host требуют независимой qualification.

Management project P одновременно является полным immutable distribution D,
вне каждого replacement target. Нужен весь existing release inventory, Core,
pf_cli/bootstrap/tools, descriptor/schemas и отдельно qualified runtime/dependencies
с проверенным isolated startup/sys.path. `construct_management` создаёт inventory,
а не relocated standalone launcher. Ни self-hash, ни synthetic fixture не заменяют
independent Q0; перенос P требует новой qualification/spec/request/capsule.

Source fixtures проверяют actual SQL/legacy producer → prepare/schema/write_once →
start/wrapper/harness → collection и barrier-controlled mutation между preflight,
reservation и consume. Измеренные локальные lock/operation timings не являются
глобальной гарантией 500 мс/400000, genuine cold, private-ACL или production readiness.
