Статус: `passed`.

Assignment: `p121-core-catalog-transfer-specializations-create-configuration-speciali`. Проверены точные identity, состояние `implementation/in_progress`, готовность без блокировок и разрешённая область записи.

Создан `src/processforge_core/configuration/specializations.py` с классом `SpecializationCatalogReader(distribution_root: Path)`.

| Исходный алгоритм → метод | full_ast_equal | signature_equal | annotations_equal |
| --- | --- | --- | --- |
| specialization_resource_id → resource_id | true | true | true |
| specialization_registry_path → registry_path | true | true | true |
| specialization_path_from_registry_entry → path_from_registry_entry | true | true | true |
| specialization_path_candidates → path_candidates | true | true | true |
| specialization_manifest_index → manifest_index | true | true | true |
| specialization_manifest_path → manifest_path | true | true | true |

Полный AST сравнен после явных разрешённых замен имён, добавления `self` и обращения к конкретным Core owners. Литералы, runtime-сигнатуры и строки аннотаций совпадают.

Использованы существующие `UpdateDocumentReader`, `ContextContractInputs`, `WorkspacePathReferenceReader`, `ProjectMetadataReader`, канонические `yaml_error` и `path_is_relative_to`. Конструктор не читает документы; корни операций передаются явно. Сохранены ранняя валидация, фильтрация кандидатов, порядок и дедупликация путей, отсутствие фильтра статусов в индексе, последнее значение ID, порядок YAML/YML, поверхностное копирование неизвестных полей и повторные чтения flow root.

Compile без импорта продукта выполнен успешно. Однократно прошли пять синтетических сценариев:

- Холодный конструктор и точное делегирование аргументов.
- Валидация до I/O, статусы, порядок кандидатов и дедупликация.
- Индекс: статусы, glob-порядок, последнее значение, неизвестные поля и источники.
- Актуальные документы, независимые корни и выбор первого существующего манифеста.
- Передача исходных исключений и причин, короткие ветви отказа.

Семь используемых замороженных зависимостей сохранили `raw_equal=true` и `ast_equal=true`. Для трёх используемых констант владельца `resources.snapshot` подтверждено полное равенство AST и значений; новые константы не введены.

SHA-256 продукта:
`b256995da80741c0028b1df041cc95e756db44f622760e7b9b78f06bed85ba08`

Доказательства находятся в `.pf/artifacts/pf121-oop-core-catalog-transfer-20261018/specializations/`: `proof.json`, `normalized-ast.json`, `verify.py`, `log.md`. Продукт завершается ровно одним переводом строки.

Архитектурные требования D01/D02/D03/D06/D07/D09/D11 и применимые R01–R12 сохранены в границах переноса. Serena/IDE недоступны; использованы объявленные замороженные входы и локальный AST-анализ.

Реальные/default/copied-Core проверки, миграция Main, интеграционная приёмка и нативные переходы остаются ответственностью родителя. Git, инфраструктура и внешние ресурсы не изменялись.
