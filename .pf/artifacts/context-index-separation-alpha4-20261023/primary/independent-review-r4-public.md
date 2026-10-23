# Portable copy of the exact independent r4 report

Original bytes SHA256: `08a716dd1a813a654179e86234f4abf9be5bc8f435905fb1ec7cd509942bf9cc`.
This derived copy normalizes line endings only; the sealed original is retained.

**READ_ACK**

Прочитаны обязательные входы r6, frozen r20, дельта, семь новых регрессионных случаев, четыре smoke-fixtures, Python/OOP excerpts и provenance, предыдущий отчёт r16 и связанные решения. Контрольные суммы предоставленных входов и капсулы совпали.

**CODE GO — для точного кандидата r20. Новых дефектов, требующих исправления, не обнаружено.**

SHA256 манифеста `source-candidate-r20.json`:

`563150ff57d8a6b9b4b2f7261c96db8df51c4a3be0d9db6d12f9c8ee4da147e9`

SHA256 и размеры **45/45 файлов совпали до и после проверки**. Дополнительно проверены **41/41 файл r16**; **38 ранее рассмотренных файлов неизменны**.

Предоставленная дельта от baseline `23ae166133390275a67ba92c1f00357bc757533a` содержит ровно семь файлов. Строгое применение каждого diff-hunk к frozen baseline воспроизводит r20:

| Файл | Проверенное изменение |
|---|---|
| `src/processforge_core/resources/local_search.py` | Коррекция unscoped empty-status |
| `tests/context_index_separation/test_review_regressions.py` | Семь новых случаев; прежние AST-узлы сохранены |
| `tools/smoke_garage_no_hooks_sessionless.py` | Явное обслуживание; predicates 6 → 9 |
| `tools/smoke_garage_session_enhanced.py` | Явное обслуживание; predicates 6 → 6 |
| `tools/smoke_garage_cross_project_security.py` | Явное обслуживание; predicates 13 → 13 |
| `tools/smoke_user_like_garage_path.py` | Work до обслуживания; predicates 6 → 9 |
| `checksums/processforge.sha256` | Обновлены пять соответствующих distribution-записей |

Все **31 исходный smoke-предикат сохранены среди 37 текущих**. Helpers эквивалентны с учётом явно записанного прежнего `check=False`. Импорты учитывают bootstrap; очистка `.codex` ограничена разрешённым каталогом fixture-проекта.

Исправление в `local_search.py:1403` устраняет подтверждённое расхождение: observation сообщал `fresh` после обслуживания пустого corpus, а повторная unscoped-проверка запроса возвращала `missing`.

Новая ветка требует нулевого физического числа ресурсов и документов, а также workplace-записи со статусом `fresh`, нулевыми счётчиками ресурсов, документов и ошибок и `allowed_resource_ids='[]'`. Используется постоянный read-only SQL-предикат. Scoped-ветка, схема и публичные поля не изменены. За пределами `index_status` AST production-модуля совпадает с r16.

Собственные stdlib/SQLite-пробы завершились **32/32 ожидаемыми результатами**: два воспроизведения дефекта на r16 и 30 проверок r20. Подтверждены:

- Свежий пустой поиск после первоначального явного обслуживания и после удаления всех зарегистрированных ресурсов.
- Очистка `resources`, `documents` и `documents_fts`; старый project snapshot не возвращает удалённое содержимое.
- Отказ для отсутствующей БД, schema-only storage, отсутствующей workplace-записи, несогласованных счётчиков, некорректных allowed IDs, несовместимой схемы и физического orphan document.
- Сохранение блокировки доступа при durable running/failed/unavailable, pending notification и несвежем обязательном контексте.
- Ограниченный отказ при настоящем exclusive SQLite lock.

Файловые reader-соединения проверялись с `mode=ro`, `timeout=0`; SQL authorizer запрещал мутации. Контроль дерева файлов подтвердил неизменность содержимого и времени модификации при чтениях. AST-разбор и компиляция успешны для **36 Python-файлов**; **32** представленные в distribution inventory записи совпали по хешам.

Прежние access, batch, notification и Main-контракты сохраняют r16-доказательства благодаря совпадению соответствующих файлов; они не выдаются за заново исполненные собственные проверки.

Проверены исходные stdout/stderr и контрольные суммы **9 pytest/static receipts, 15 affected native checks, четырёх corrected smokes и семи CLI-вызовов**. Прочитаны реальные red/green-результаты: **2 failed, 5 passed** перед исправлением и **60 passed** после него.

По подтверждённым receipts primary:

- Полный pytest: **732 passed, 7 skipped, 246 subtests passed**.
- Ruff lint/format: 34 файла и отдельно извлечённые изменённые Main-функции.
- Strict mypy: 14 production-модулей.
- Bandit: десять модулей, без findings.
- Покрытие девяти новых модулей: statements **95,28%**, branches **91,03%**; это не покрытие всего репозитория.

Собственные пробы использовали Python 3.14.3, SQLite 3.50.4 и реальные frozen-модули. Catalogue, проверенный context, YAML serializer, clock и navigation ports моделировались. Зарегистрированные pytest/static/native/CLI-прогоны самостоятельно не повторялись.

Первая собственная попытка остановилась на правах каталога `tempfile`; результат сохранён. После изменения только способа создания собственной fixture все 32 группы прошли. Serena/IDE MCP отсутствовали; использованы ограниченное чтение и AST.

**Семь skips и шесть SQLite ResourceWarning остаются ограничениями.** Исходный failed source gate, filtered diagnostic и user-like failure r19 сохраняются как неуспешные доказательства. Они не квалифицируют релиз.

Полные повторные unfiltered source и exact consumer archive gates, новый обычный commit/push и последующая доставка остаются ответственностью primary. Installed, connected-host, native POSIX acceptance, tag и публикация этим review не подтверждаются.

Продуктовые файлы, Git, PF lifecycle, инфраструктура, live workplace и прежние кандидаты не изменялись; subagents не использовались.

**RESULT: pass — CODE GO для точного r20 в указанных пределах доказательств.**