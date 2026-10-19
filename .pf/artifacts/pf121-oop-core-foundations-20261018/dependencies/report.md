# Отчёт dependencies

Статус: реализация и ограниченные проверки пройдены. Переходы PF выполняет primary.

Назначение: `p121-core-foundations-dependencies-create-project-requirements-py-platfo`.
Run: `garage-p121-core-foundations-dependencies-create-project-requirements-py`.
Context: `p121-core-foundations-dependencies-create-project-requirements-py-platfo-capsule`.
SOURCE `work-state` подтвердил стадию `implementation`, валидность контекста, готовность и отсутствие блокировок.

Создан `src/processforge_core/project/requirements.py`: холодный `PlatformDependencyPreflightService(distribution_root)` компонует `ProjectPackageCatalogReader`, объявленный peer `TemplateCatalogService` и `ContextContractInputs`. Методы `check` и `registry_ids` получают workplace на каждой операции. Реестр читается по буквальному `workplace_root / "registries" / registry_name`; идентификаторы извлекает каноническая `common.values.registry_ids`.

Сохранены truthiness списка manifests, проверка template через `is None`, безусловное чтение tools затем MCP после циклов, порядок и дубликаты отсутствующих ресурсов, точное сообщение `SystemExit`, YAML-error-семантика, свежие наблюдения и исходные исключения с cause. Нет обратной зависимости на Main/Host, кэша документов или новых правил.

Проверки:

- Полный нормализованный AST обоих исходных алгоритмов совпал по всем узлам и литералам. Сигнатуры и строковые аннотации совпали. Разрешённые переименования и хеши AST приведены в `proof.json`.
- Исходник скомпилирован без импорта продуктовых модулей. Пятнадцать неизменённых frozen owners совпали побайтово и по AST. Mutable peer `common/values.py` не читался; использован замороженный before-image.
- Ровно пять синтетических сценариев прошли один раз: порядок/дубликаты/truthiness; пустые требования, смена workplace, повторные чтения, YAML-error и aliases; отказ package с cause; отказ template; отказ MCP-чтения до сводного сообщения. Полные traces и результаты baseline/service совпали.
- `proof.json` прочитан после создания; проверены status, результаты и финальный хеш продукта.

Архитектурная привязка: D01/D02/D03/D09 — конкретная композиция и owning Core; D06/D07 — прежние проверки и ошибки; D11 — ограниченный перенос. Применимые R01–R12 не расширены; R06 подтверждён повторными наблюдениями, R10 — раздельным владением, R12 — отсутствием частных абсолютных путей в отчёте. Использованы объявленные архитектурные документы, Python material/provenance и frozen concrete dependencies.

Финальные raw SHA256:

- `src/processforge_core/project/requirements.py`: `08026d4dbcbe0ff0bd71958a16eb1ed98224bad43ce667fc8cd5733637d5a96d`.
- `proof.json`: `306efa43f9ef6b029dcc052a8867de86f77625b4729d7309e1d49ad59304dfd5`.
- `verify.py`: `445710cab87a402f0b094992e58321b893b237fa72af8182a35420585fd87cf0`.

Изменены только собственный product и артефакты dependencies (`proof.json`, `verify.py`, `log.md`, этот отчёт). Реальных workplace-записей, продуктовых импортов, Git-мутаций, инфраструктурных действий, вложенных агентов и lifecycle-переходов не было.

Осталось primary: миграция consumers, реальные scratch I/O, direct/copied Core composition/imports, затронутые existing scripts и независимый review. Готовность archive/installed/Runtime/connected-host не заявляется.
