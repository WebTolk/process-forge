# Чтение сессий, специализации, кандидаты и перенос обновлений

Реализация и ограниченная проверка завершены на базе
67951028756a22d0bf7f1efa17388682f1c49a60. Для независимого ревью закреплены
девять итоговых продуктов: пять файлов четырёх native contributors и четыре
файла primary. В prose исходного brief ошибочно указано шесть worker products;
его явная ownership map содержит правильные пять путей. Scope/pins не менялись.

ProjectSessionReadService владеет прежними report_status, recent_files и legacy
freshness: первый regex match, UTF8 replacement, stable mtime-desc sort, срезы,
повторные stat и raw substring fingerprint checks сохранены. Современный context
freshness и report lifecycle не заменены этой legacy проекцией. Общий COLON_WS
перенесён в common.text; весь прежний raw prefix и AST этого модуля сохранены.

SpecializationCatalogReader владеет шестью существующими алгоритмами ID, registry
path, кандидатов, manifest index и первого файла. Готовые paths/containment/ID
guards, YAML и metadata owners переиспользованы. Корни передаются на операцию;
distribution_root используется как настоящий immutable anchor для stateless
path guards. Сохранены early validation, фильтрация missing/disabled только в
candidates, ordered dedup, YAML/YML glob order, отсутствие фильтра в индексе,
последний победитель ID, shallow unknown fields, Path values и fresh reads.

KnowledgeCandidateValidationService собирает готовые targeting/privacy policies
с исходным порядком checks. Категории перенесены точным set assignment; Main
импортирует то же имя для остальных consumers/parser choices. Строгие проверки,
fallback, Unicode JSON, native errors и findings сохранены. Новых policies нет.

UpdateTransferService использует существующие site/document owners. Local copy2,
HTTP stream/copyfileobj, timeout 15/30, with/open order, имена, warnings и errors
точны. Read/decode manifest остаются внутри Exception catch, text parser снаружи.
Artifact errors и partial destination semantics сохранены; нет нового mkdir,
retry, atomic write, проверки hash или archive inspection. Конструкторы холодные,
parsed documents/current project не удерживаются, обратных callbacks в Main нет.

Native proofs подтверждают полные двенадцать algorithms, signatures/annotation
strings, две константы, prior owners и 19 синтетических случаев без повторов.
Primary подтвердил 90 сравнений с десятью native exceptions: реальные scratch
reports/registries/globs/guards, same-size/same-mtime/read-after-write/create/delete,
упорядоченные checks, local/stubbed HTTP и exact bytes. Прямой и copied Core
импортируются и собираются без Main/Runtime. Сеть в HTTP characterization заменена.

Все восемь affected existing scripts прошли с первого запуска: specialization
registry/context resolution/project override, candidate schema/targeting schema,
update candidate discovery, session start context check и docs contract. Новых
постоянных тестов или широких release/archive/install/Runtime/connected-host/ZIP
проверок нет. Успешные сценарии не повторялись.

Из Main удалены 12 функций и два присваивания констант. Полный упорядоченный AST
688 оставшихся определений содержит только объявленные canonical imports,
четыре холодные композиции и новые method targets. Полный selected identifier scan
не выявил внешних function consumers; совпавшие context_freshness строки — поля
JSON, они сохранены. EN/RU ownership обновлён. Inventory: четыре изменённых строки,
четыре новых, 1379 сохранены; известный посторонний drift не затронут. Inventory
использует LF Git bytes, final manifest хранит raw working-tree hashes отдельно.

Приёмка source-only, внешние контракты 1.2.0 сохранены. OOP-эпики остаются открытыми.
После независимого review — selected commit в оба dev remote с existing GitVerse
token, полный SHA readback, закрытие шести exact Work/root doctor и перечитывание
девяти исходных architecture inputs. Посторонний dirty/index state сохраняется.
