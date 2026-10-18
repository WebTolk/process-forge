# Отчёт updates

Статус: **PASS в пределах назначенного source-scope**.

Assignment: `p121-core-audits-updates-create-maintenance-validation-py-updatedocument`  
Run: `garage-p121-core-audits-updates-create-maintenance-validation-py-updated`  
Context: `p121-core-audits-updates-create-maintenance-validation-py-updatedocument-capsule`  
Attempt: `1`.

Точное состояние Work проверено через SOURCE CLI: implementation, контекст valid, readiness ready, blockers отсутствуют. SHA-256 immutable capsule и всех 32 обязательных файловых входов подтверждены.

Создан `UpdateDocumentValidationService(distribution_root: Path)` с методами `site_overrides` и `normalized_manifest`. Конструктор собирает существующие `UpdateSchemaChecks` и `UpdateSourceContractPolicy` без I/O. Перенесён точный `SHA256_HEX_RE`.

Существующий `UpdateRegistryReader` дополнен `installed_versions`: сохранены отдельная фильтрация строковых type/id/version, непустая version и правило последней записи. Существующий `UpdateDocumentReader` дополнен `staged_path` и `staged_record`: candidate ID используется дословно; чтение делегируется прежнему soft-YAML reader.

Подтверждено:

- Полное нормализованное AST-равенство пяти переносимых функций, включая порядок guards, циклов, полей, проверок, schema append, сообщений и PASS fallback.
- Совпадение сигнатур за исключением добавленного `self`, строк аннотаций и future annotations.
- Полное AST-равенство обоих прежних модулей после удаления исключительно добавленных методов: конструкторы, поля, импорты, данные и прежние методы сохранены.
- Compile трёх полных модулей без выполнения импортов.
- Пять синтетических сценариев на извлечённых определениях: ранний отказ пустого документа; overrides с дубликатами и original/preserved environment checks; вложенные manifest-проверки URL/hash; фильтрация installed versions и текущие чтения; дословный staged path и текущие чтения. Результаты, порядок вызовов и проверенные native OSError совпали.
- `git diff --check` прошёл. Изменённые product-файлы и созданные evidence-файлы заканчиваются ровно одним переводом строки.

Машиночитаемые доказательства: `.pf/artifacts/pf121-oop-core-audits-20261018/updates/proof.json`. Воспроизводящий скрипт: `verify.py`; подтверждение входов: `input-verification.json`; журнал: `log.md` в том же каталоге.

Итоговые raw SHA-256:

| Файл | SHA-256 |
|---|---|
| `src/processforge_core/maintenance/validation.py` | `feae84e6799d1f1af66389327e35de2337d086002c019e3253087dddeef4d5fc` |
| `src/processforge_core/maintenance/documents.py` | `3a8e4f207f40a534860259323bb876f439c9e48fdaf6f327b5dcb1cf958eb552` |
| `src/processforge_core/maintenance/registries.py` | `c573cab64fad82959e1c97342db9db771aef120335f5784c487d5d5f8d4af75a` |

Архитектурная сверка: D01/D02/D03/D09/D11 соблюдены выделением ответственности и конкретной композицией без обратной зависимости от монолита/Host. D06 и R01–R12 сохранены в границах среза: полномочия, identity, lifecycle, mutation и recovery не изменялись; текущие чтения и ownership сохранены.

Использованы закреплённые архитектурные документы, Python material/provenance и frozen dependencies. Serena/IDE недоступны; применено файловое чтение объявленных входов.

Миграция consumers, выполнение default assembly, live fixtures, suites и native transitions остаются за primary. Package/archive, installed и connected-host границы здесь не проверялись. Git mutation, remote access, инфраструктурные действия и вложенные агенты не использовались.
