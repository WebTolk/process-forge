# Отчёт indexes

Статус: passed. Реализация ограниченного среза завершена; переходы Work выполняет Main.

Identity: project `process-forge`; run `garage-p121-core-resources-indexes-create-resources-index-checks-py-know`; assignment `p121-core-resources-indexes-create-resources-index-checks-py-knowledgere`; context `p121-core-resources-indexes-create-resources-index-checks-py-knowledgere-capsule`. SOURCE CLI подтвердил implementation, valid, ready и отсутствие блокировок.

Изменены только два product-файла:

- `src/processforge_core/resources/index_checks.py`: создан `KnowledgeResourceIndexService(distribution_root: Path)` с `index_path`, `path_ref_missing`, `project_checks`.
- `src/processforge_core/common/paths.py`: добавлен исходный `path_is_relative_to`; прежние байты, imports и полный AST сохранены.

Три метода используют конкретных владельцев Core: `ProjectPackageCatalogReader`, `ContextContractInputs`/его `YamlDocumentReader`, `ResourceRecordService`, `PlatformDependencyPreflightService.registry_ids`, `WorkspacePathReferenceReader`. Конструктор холодный. Path reader создаётся с workplace текущей операции после раннего возврата для `package.yaml`. Аргумент операции `distribution_root` сохранён отдельно от distribution root сервиса. `HEAVY_RESOURCE_KINDS` импортируется из peer records.

Для всех четырёх originals доказано равенство полного AST после перечисленных в `proof.json` замен имён/receivers и удаления единственного разрешённого assembly statement. Сохранены сигнатуры и annotations, литералы, шесть registry mappings, package-only/external exemptions, skips, root selection, порядок диагностики и native exceptions. Helper разрешает оба пути и перехватывает только `ValueError`.

Проверки: компиляция обоих текстов без импортов продукта; неизменность raw bytes и AST 17 frozen dependencies; пять синтетических случаев на извлечённых определениях и stubs, каждый выполнен один раз:

1. Холодная сборка, ранний возврат, flat fallback, workplace операции, сохранение объекта native exception.
2. Guards и exemptions path_ref, все шесть mappings, свежий registry read, неизменность входов.
3. Все manifest skips и результат при отсутствии ресурсов.
4. Три index branches, выбор roots, порядок resource diagnostics, повторная операция после изменения документов.
5. Разрешение обоих аргументов helper, `ValueError` и распространение исходного `OSError`.

Прочитаны закреплённые clarification, migration contract, progressive OOP decision, ADR/domain/direction, OOP-02/03/05, Core AGENTS, brief, полный reference baseline для назначенных алгоритмов, frozen concrete dependencies и PF Python excerpts/provenance: `simple-statements.md` 454–480, `pep20.md` 39–57. Serena использована для обзора common.paths. Сохранены применимые D01/D02/D03/D06/D07/D09/D11 и R01–R12: конкретная композиция, исходные guards и live reads, отсутствие обратного пути к Main/Host, неизменность контекста и границ scope, portable отчёт.

Доказательства: `proof.json`, `observations.json`, `verify.py`, `log.md` в каталоге данного отчёта. `proof.json` содержит полный mapping originals, AST hashes, signature observations, substitutions, product hashes и сохранность прежних владельцев; `observations.json` содержит трассы пяти случаев.

Граница проверки: assembled imports, реальные scratch fixtures, affected scripts, Main consumer migration и независимое review остаются Main. Runtime, archive, installed, connected-host и release qualification здесь не выполнялись. Peer sources не использовались как входы; Main, docs, inventory и peer-файлы не изменялись. Git/remote/infrastructure operations, вложенные агенты и lifecycle transitions не выполнялись.

Итоговые SHA256 исходных байтов:

| Product | SHA256 |
| --- | --- |
| `src/processforge_core/resources/index_checks.py` | `577f08d82d84197d91b299492caccb99578b36c252ab7b0b83350598a9490ef0` |
| `src/processforge_core/common/paths.py` | `9f26e32ffca53adb3ef45f55771cdb3e12d6099bfdeecbf241a49717f8fe9aff` |
