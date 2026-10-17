# Документационные изменения

Изменены ровно5плановых текстов и checksum inventory: notesEN/RU теперь содержат принятые SQLite/YAML/Garage/Runtime правила и текущие ограничения, migrationEN/RU описывает controlled journal cutover/backup и отдельный actual host reload, CHANGELOG группирует принятый объём под1.2.0.

Inventory регенерирован существующим валидатором в чистой detached основе с overlay только5docs. Первое обновление inventory из dirty root затронуло частную конфигурацию; оно заменено результатом чистой основы до commit. Проверено: ровно5изменённых записей inventory, hash проектной конфигурации в нём не изменился.

Проверены25относительных ссылок, устранены ложные отрицания cache, сохранено точное исполняемое дерево d5947ea. Raw docs-checks.json содержит фактическое количество проверенных ссылок; этим текстом отдельный smoke/независимый reviewer не заявляются. Следующий этап: review точного diff, clean commit и native candidate qualification без увеличения таймаутов.
