# Registry: перенос алгоритмов в Core

Статус: **PASS в пределах worker scope**. Реализованы `WorkplaceRegistryWriter(distribution_root: Path).upsert(path, collection_key, entry)` и standalone `common.values.upsert_resource`.

Identity: project `process-forge`; run `garage-p121-core-foundations-registry-create-project-registry-write-py-w`; assignment `p121-core-foundations-registry-create-project-registry-write-py-workplac`; context `p121-core-foundations-registry-create-project-registry-write-py-workplac-capsule`.

Точное SOURCE CLI `work-state` подтвердило implementation, valid/ready, blockers=[] и разрешённые read/write_product/write_artifact. Собственные lifecycle transitions не выполнялись.

## Изменения

- `src/processforge_core/project/registry_write.py`: полный прежний `upsert_registry_entry` принадлежит `WorkplaceRegistryWriter`. Холодный конструктор сохраняет явный distribution_root и создаёт конкретные `YamlDocumentReader(_parse_simple_yaml)` и `UpdateSchemaChecks(distribution_root)`. Путь workplace передаётся каждой операции через path; документы не кэшируются.
- `src/processforge_core/common/values.py`: добавлен точный алгоритм `upsert_resource`; прежние raw bytes, полный AST и imports сохранены. Список остаётся тем же объектом, заменяется первое совпадение строкового id; иначе добавляется исходный resource. Возвращаются прежние `updated`/`added`.

Сохранены все 12 registry/schema mappings, порядок guards и наблюдений, YAML errors, неизвестные поля и неизвестные имена реестров, schema exception tuple `(OSError, json.JSONDecodeError, KeyError, ValueError)`, явная причина SystemExit, `errors[:8]`, parent mkdir, UUID temporary name в том же каталоге, write_text, os.replace и finally exists/unlink с исходным приоритетом ошибок. Используются канонические yaml_error, ensure_trailing_newline и dump_yaml. Обратных зависимостей к Main/Host и aliases не добавлено.

## Доказательства

`proof.json` содержит полное сравнение AST всех узлов и литералов обоих исходных алгоритмов, hashes нормализованного AST и сигнатур, равенство runtime annotation strings, точные разрешённые преобразования имён, все schema mappings и полные наблюдения сценариев.

Прежний `values.py` подтверждён через raw_prefix_equal/full_prior_ast_equal; единственное добавление — upsert_resource. Для 15 остальных frozen dependencies подтверждены raw_equal/ast_equal. Обе изменённые исходные программы скомпилированы без импорта продуктовых модулей; future annotations сохранены.

Ровно пять синтетических сценариев прошли на исходных и перенесённых извлечённых definitions с равенством полных traces:

1. Added в известный реестр: schema read/validate, mkdir, UUID stage, запись, replace, проверка отсутствующего stage.
2. Updated в неизвестный реестр: первое совпадение id, сохранение второго совпадения, общего списка, borrowed entry и неизвестных данных; schema read пропускается.
3. Schema refusal: исходный KeyError сохранён как явная причина SystemExit; filesystem mutations отсутствуют.
4. Ошибка stage write: finally проверяет и удаляет частичный stage перед распространением исходного OSError; replace не вызывается.
5. Ошибка replace с ошибкой cleanup: PermissionError очистки имеет исходный приоритет, OSError replace сохраняется в exception context.

Успешные сценарии повторно не запускались. Реальных записей в workplace и прямых/копированных импортов Core не выполнялось.

## Финальные raw SHA256

| Файл | SHA256 |
| --- | --- |
| `src/processforge_core/project/registry_write.py` | `aeb4f46bdfae83dbbe86f1dcdb1ea98c36d1d11c60ce7cbfb25b87d3ef2f94c3` |
| `src/processforge_core/common/values.py` | `8f6d3372fd162e5a2cbdbf5dedeb3b3295ce194327d44dce2b7fdb684d6a9a8a` |
| `.pf/artifacts/pf121-oop-core-foundations-20261018/registry/proof.json` | `1168e1294087047d206b39248a2633f7bafd8c4698488c714f5cdb5dcf28af3c` |

Входы: закреплённые девять архитектурных документов, brief, baseline-functions.json, frozen concrete dependencies и локальные Python excerpts simple-statements.md:454–480 / pep20.md:39–57. Их происхождение и hashes отражены в proof.json. Serena использована для обзора values.py; инфраструктурных блокировок не возникло.

Срез сохраняет D01/D02/D03/D06/D07/D09/D11 и применимые R01–R12: конкретные Core owners, холодная композиция, прежние storage/errors и live observations, неизменённые identity/access/lifecycle, один writer и portable отчёт. Это не приёмка архитектурных эпиков.

Handoff primary: удалить исходные определения и мигрировать actual callers в своём scope; выполнить предусмотренные реальные scratch I/O, direct/copied Core composition и affected existing scripts; провести независимый review по указанным финальным product hashes и штатные transitions. Worker не менял Main, docs, inventory, peer products, Git или инфраструктуру. Task-local verifier сохранён как evidence: `.pf/tmp/p121-core-foundations/registry/verify.py`.
