# Уточнение DB-задачи: SQL отдельно от открытого вопроса поиска

Статус результата: требования записаны; реализация DB-задачи не начата.
Исходная задача pf-database-layer-and-journals-20261021 остаётся открытой.

## Задание, контекст и режим

Оператор подтвердил одну основную SQLite-базу рабочего места и проектные
базы в `.pf`, затем оставил размещение поискового индекса на исследование.
Бухгалтерия остаётся SQLite/SQL с возможностью будущих SQL-адаптеров.
Плановый successor имеет valid/ready immutable capsule, один writer и только
read/write_artifact. Старый input-only backlog не расширен; предыдущая
формулировка с mandatory search merge отменена через native cancel и handoff.

## Scope и investigation

Записываются requirements.md, research.md и current-requirements.json.
Читаются исходные требования, локальная документация и официальные SQLite
isolation/WAL/FTS5. Ключевой результат исследования: конкуренция writers
сохраняется между таблицами одного файла; FTS maintenance может быть тяжёлым.
Практического benchmark PF нет; размещение поиска остаётся undecided.
Методика и источники находятся в research.md.

## Domain и граница архитектуры

SQL accounting/operations — подтверждённый владелец основной базы; проектные
данные сохраняют отдельный уровень и portability. История и текущее состояние
имеют разные предметные операции и не требуют отдельного файла на модуль.
Retrieval/RAG имеет отдельную логическую границу. Общая или отдельная
физическая база поиска, backend, embeddings и новые SQL drivers не выбраны.
Принята только фиксация требований, не полный технический дизайн реализации.
Grant/project isolation и прежние публичные/file-only контракты сохраняются.

## План изменения и его выполнение

Оригинальные spec/research/card/capsules остаются неизменными. Новая ревизия
и индекс текущих требований явно задают более позднее уточнение оператора.
Продуктовая реализация not_applicable: изменены только новые плановые документы,
ссылки и append-only log. Продукт, базы, сервисы и зависимости не изменялись.
Ни миграция, ни обслуживание поиска, ни RAG, ни agent scheduler не запускались.

## Assurance

Для документального изменения проверяются JSON/ссылки/утверждения scope,
хеш requirements pointer, неизменность исходных входов и главного Git index;
проверенные результаты записываются в validation.json. Нового исполняемого
продуктового кода нет: pytest/Ruff/mypy и browser tests not_applicable.
Независимый code review not_applicable: scoped planning-only requires_review=false;
primary не выдаёт собственную проверку за независимый review. Native run/capsule
doctors сохраняются отдельно после завершения lifecycle.

## Delivery и evolution

Release/profile/package/install not_applicable: это плановая ревизия требований.
Только собственные документы фиксируются и публикуются в оба dev remote с
токеном GitVerse и полным readback. Original dirty checkout/index сохраняются.
Delivery receipt фиксируется после фактического push; до него публикация
не объявляется выполненной.

Дальнейшая DB-реализация должна читать current-requirements.json вместе с
исходной spec. Обязательное включение поиска в SQL не подтверждено, отдельный
поисковый файл также не утверждён. Новый RAG или глобальный agent scheduler
этим уточнением не регистрируются. Memory, process definitions и исторические
planning карточки не редактируются.
