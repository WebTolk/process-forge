# Отчёт updates

Статус: **PASS — назначенная реализация завершена**.

Создан `src/processforge_core/maintenance/candidate_read.py`: `UpdateCandidateReader(distribution_root: Path)` с методами `read(workplace_root)` и `find(workplace_root, candidate_id)`.

Использованы существующие `UpdateDocumentReader` и `maintenance.update.now_utc`. Сохранены три повторяющихся fallback-словаря, свежие чтения, неизвестные поля, исходное сравнение ID, первый подходящий элемент без копирования и распространение нативных ошибок. Конструктор не выполняет I/O и не вызывает часы.

Проверки выполнены однократно:

- Компиляция без импорта продуктовых модулей.
- Полное равенство AST, сигнатур и аннотаций обеих исходных функций после разрешённых замен.
- Побайтовое и AST-равенство существующих `documents.py` и `update.py` frozen-входам.
- Пять модельных сценариев: холодный конструктор; три fallback-ветви; свежие чтения с явными корнями; raw ID equality и borrowed identity; распространение `OSError`/`UnicodeDecodeError`.

Доказательства: `proof.json`, `verify.py`, `log.md`, `changed-files.json`, `change-summary.md` в назначенной области artifacts/updates.

SHA256 продукта:

`22e7789dc700242a1540b7791a726400517212d7e35976fe23d67057f7ba027d`

Применимые D01/D02/D03/D06/D07/D09/D11 и R01–R12 сохранены в границах среза. Реальная композиция, миграция consumers, интеграционные проверки, независимый review и переходы PF остаются основному агенту.