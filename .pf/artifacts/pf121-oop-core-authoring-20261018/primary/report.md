# Модели и чтение авторинга, представление процессов и кандидаты

Реализация и ограниченная проверка завершены. Для независимого ревью закреплены
14 продуктов на базе 777d3b145f12a27ec317f2628795ca89f3189b8f.

В authoring.plans перенесены точные изменяемые AuthoringWrite, AuthoringEffect,
AuthoringPlan и AuthoringPlanRenderer. Decorators, поля/defaults/default_factory,
порядок, сигнатуры, future/string annotations, mutation/equality/repr/asdict
и fresh payloads сохранены. Смена модуля — объявленное перемещение модели.
Renderer сохраняет порядок stdout, сортировку строк, conditions/schema suffix,
исходные ошибки и передачу root; callback-данные не исполняются.

AuthoringInputService владеет режимом, путями transaction/journal, незавершёнными
журналами, проверками и цепочкой родителей через готовый YAML reader. Soft YAML,
неизвестные/nonterminal состояния, sorted glob, terminal set, повторные exists/
is_dir и исходные отказы сохранены. Два guarded/raw digest алгоритма добавлены
в существующий FileDigestReader; прежний streaming-метод, dataclass contract,
imports, raw prefix и полный прежний AST точны. Main использует готовый instance.

ProcessAuthoringExampleBuilder и process_yaml_content владеют семью прежними
path/bytes документами. Сохранены Unicode, YAML/Markdown литералы, порядок ключей,
paths, truthiness и native failures. В существующий ProcessParityRenderer добавлен
только index и необходимый canonical import. Все прежние методы и байты после
обратного удаления этих вставок точны. Main использует прежний instance.
Общая aggregate_status расположена в common.status без нового класса/политики.

UpdateCandidateReader использует прежние пути UpdateDocumentReader и существующие
часы maintenance.update.now_utc: полный AST clock совпадает с прежним Main helper.
Сохранены три fallback-словаря, свежие чтения/время на fallback, JSONDecodeError-only,
прочие ошибки, raw ID equality, first match, borrowed item и unknown fields.
Новых часов, Main callbacks, cache или constructor I/O не добавлено.

Два фактических consumer scripts используют canonical models и journal paths
локально в существующих операциях после прежнего bootstrap. Полный AST/raw proof
подтверждает сохранность assertions, fixtures, failure callbacks и phase matrices.
Полный поиск выбранных имён включает attributes любых aliases, exact strings
и direct imports; других внешних source consumers не обнаружено.

Четыре native-вклада приняты по фактическим отчётам/итоговым raw hashes. Полные
18 definitions, включая три класса, signatures/annotations/data и prior owners
подтверждены. Native synthetic proof сохранён без повторного исполнения.
Primary подтвердил 85 сравнений, включая 18 карт аннотаций, три field maps,
stdout/инертность callbacks, реальные journals/path guards/raw digests, семь
документов, Markdown/status projection, candidate JSON/default/error/read-after-write
и same-size/same-mtime поведение. Семь native exceptions совпали. Прямой и
скопированный Core работают без Main/transport. Clock фиксировался только в
характеризации, без нового product port.

Все пять affected existing scripts прошли с первого запуска: authoring crash
recovery, remediation transactional authoring, process authoring materialization
parity, update candidate discovery и docs current code contract. Успешные сценарии
не повторялись. Это bounded source assurance; Runtime/сервис не запускались,
широкие release/archive/install/connected-host/ZIP проверки не выполнялись.

Из Main удалены 18 определений (15 функций/3 класса) вместе с decorators.
Полный упорядоченный AST 700 оставшихся определений содержит только объявленные
импорты, четыре холодные композиции и миграцию вызовов; существующие digest/parity
instances переиспользованы. EN/RU ownership обновлён. Inventory меняет семь строк,
добавляет шесть, сохраняет 1370 остальных и три известных посторонних расхождения.

Приёмка source-only, внешний контракт 1.2.0 сохранён. Preflight/callback execution,
failure injector, staging/publication/commit/rollback явно остаются у прежнего
владельца; этот срез их не переносит и не изменяет. OOP-эпики открыты. После ревью
следуют один selected commit в оба dev remote, полный SHA readback, завершение
шести Work/root doctor и полное перечитывание девяти architecture inputs.
GitVerse использует существующий токен без credential helper/tracing; посторонние
dirty/index изменения сохраняются.
