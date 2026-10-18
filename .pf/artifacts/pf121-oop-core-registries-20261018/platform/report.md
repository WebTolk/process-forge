**Результат:** реализация платформенного среза выполнена в выделенном scope. Проверки нормализованных AST, сигнатур, аннотаций и сохранности существующих классов прошли. Интеграционная проверка assembled Core и миграция callers остаются у родителя.

**Identity**

- Project: `process-forge`
- Run: `garage-p121-core-registries-platform-create-projectplatformselectionserv`
- Assignment: `p121-core-registries-platform-create-projectplatformselectionservice-dis`
- Context: `p121-core-registries-platform-create-projectplatformselectionservice-dis-capsule`
- Capsule checksum: `sha256:d2a0637b84790e51fd7b6cde9da3bf514f951976b4aac8b6458008218daa0b9f`

Точный source CLI `work-state` подтвердил `implementation`, `valid`, `ready`, отсутствие blockers и соответствие разрешённых действий и файлов prepared input. Lifecycle-переходы не выполнялись.

**Изменения**

Создан `ProjectPlatformSelectionService(distribution_root: Path)` со следующей картой переноса:

| Frozen-функция | Метод службы |
|---|---|
| `selected_project_platforms` | `selected` |
| `platform_contract_project_type_hints` | `project_type_hints` |
| `platform_contract_parent_type_hints` | `parent_type_hints` |
| `workplace_platform_ids_for_project_type` | `ids_for_project_type` |
| `platform_ids_from_detection_rules` | `detected_ids` |
| `platform_resource_findings` | `resource_findings` |
| `platform_binding_matches` | `binding_matches` |
| `optional_platform_resource_warnings` | `optional_warnings` |
| `forbidden_base_technology_platform_reference` | `forbidden_base_reference` |
| `available_platform_contract_records` | `available_records` |

Служба использует конкретные `PlatformContractReader`, `PlatformContractPolicy`, `ProjectDetectionService`, `ProjectPackageCatalogReader`, `AnswersDocumentReader`, `YamlDocumentReader` и `WorkspacePathReferenceReader`. Конструктор собирает зависимости без I/O. Project/workplace roots передаются на операцию; фиктивный root и сохранённое состояние документов не добавлены.

Расширены существующие владельцы:

| Владелец | Добавление |
|---|---|
| `AnswersDocumentReader` | `strings` с исходной рекурсией |
| `PlatformContractReader` | `normalize_id_pair` |
| `YamlDocumentReader` | `policy` |
| `project.classification` | `normalize_hint`, `hint_matches` |
| `common.values` | `registry_ids` |

Сигнатура policy:

```python
policy(self, name: str, root: Path | None = None, *, distribution_root: Path) -> dict[str, Any]
```

Алгоритм сохранён: `(root or distribution_root) / "policies" / name`, прежний guard `is_file`, чтение через `self.load`, прежняя обработка mapping/YAML error. Новый selection service передаёт `distribution_root=self.distribution_root`.

**Доказательства совместимости**

Прочитаны обязательные архитектурные документы, brief, Python material/provenance, три reference-specs, Core `AGENTS.md`, полный `baseline-functions.json` и все 21 frozen dependency input. Serena использована для первоначального анализа существующего `PlatformContractReader`.

До записи исходников успешно выполнены:

- Полное сравнение нормализованных AST всех **16/16 операций**: десять методов selection и шесть дополнительных операций.
- Сравнение всей прежней структуры **5/5 существующих модулей** после исключения только объявленных добавлений.
- Компиляция всех шести итоговых исходников.

Нормализация ограничена именем метода, добавленным `self`, заменой точных владельцев вызовов и явно разрешённой зависимостью policy. Для policy удаляется только дополнительный обязательный keyword-only параметр при сравнении; `distribution_root` сопоставляется прежнему `ROOT`, `self.load` — прежнему `load_yaml_document`. Литералы, docstrings, guards, порядок выражений, defaults и остальные аннотации не нормализовались.

Сохранность прежних модулей подтверждена целиком:

| Модуль | Результат |
|---|---|
| `common/values.py` | Все прежние определения и данные сохранены |
| `documents/answers.py` | Прежний класс и `read` сохранены |
| `documents/reader.py` | Dataclass, frozen-декоратор, поле `fallback` и все прежние методы сохранены |
| `project/classification.py` | Прежний класс и методы сохранены |
| `project/platforms.py` | Прежний constructor, поля и все методы сохранены |

Изолированная компиляция исходных AST с исходным `from __future__ import annotations` подтвердила **16/16 runtime-сигнатур и словарей `__annotations__`** после указанной нормализации. Для дополнительного параметра policy отдельно проверены имя, строка аннотации `Path`, keyword-only kind и отсутствие default.

Frozen baseline соответствует commit `a32c4828fee3a10988026007f8a9089bfcebc226`. SHA исходного монолита подтверждён с учётом Git LF → worktree CRLF; future annotations подтверждены по этому baseline. Проверка не импортировала монолит.

Полные записи по каждой операции — исходное имя, target, аргументы, return annotation и normalized AST SHA — содержатся в `proof.json`. Runtime-сигнатуры, полные словари аннотаций и результаты сценариев содержатся в `verification.json`.

**Пять синтетических сценариев — PASS**

1. Рекурсивные answers сохраняют порядок, повторы и whitespace; tuple исключается. Registry aliases сохраняются независимо от статуса. `normalize_hint` вызывается дважды для каждого рассмотренного значения; short-circuit сохранён.
2. Selection сохраняет порядок detection/index и переданные roots. Inherited base hints не продвигают descendants; собственный specific hint выбирает derived contract. Цикл родителей завершается без изменения входного `visited`.
3. Findings сохраняют порядок чтений package registry → catalog → tools → MCP metadata → templates, исключение `__duplicates__`, повторяющиеся required findings и точные required/recommended payloads.
4. Available records сохраняют literal statuses, aliases, дубликаты и raw source. Пропускаются именно `missing`/`disabled`; uppercase status сохраняется. Binding guards сохраняют truthiness `process_id` и stack fallback.
5. Policy сохраняет root override, порядок наблюдений, alias возвращаемого mapping и неизвестные поля. Missing/invalid/nonmapping YAML обрабатываются прежним образом. Forbidden-base проверка сохраняет EN/RU markers и одинаковый native `TypeError`, сообщение и cause для некорректного списка.

**Финальные raw SHA-256**

Пути ниже относительно `src/processforge_core/`.

| Файл | SHA-256 |
|---|---|
| `common/values.py` | `f7bcc6434d68d7591d3c310bc01ab6e84b15394e785dbad5c2a1d43d48f56702` |
| `documents/answers.py` | `331f602047ffa16e53176d0f4de5fbe6a0b2dac0f714e9161e6b632cc8964776` |
| `documents/reader.py` | `ccc98655202bc9b01c2ae9aae57e8eefb3b87f226bff611e0a0cb4df7bd547bf` |
| `project/classification.py` | `ea4d6ab14135eced28d1b76cf8b37708d25e09d670be39457bfc4a24eca69892` |
| `project/platforms.py` | `b28771560b3efdfdf5bfcac5bcb154fea5a5a7f5504d4a32970b028af9ad31c9` |
| `project/platform_selection.py` | `ace870c7f64d1a77e11e5f1cf8f6d737a93d8bcda8926f49655011f042f99887` |

Evidence в `.pf/artifacts/pf121-oop-core-registries-20261018/platform/`:

| Артефакт | SHA-256 |
|---|---|
| `proof.json` | `04006cef6916361c11624f7d10ab689d0d9bc39fe604af7cd2796df91470b691` |
| `verification.json` | `0ab516c4e2086486c6ee947a45fcaac56ab80edca60f5a5b7004675eadebea0c` |
| `log.md` | `afe0f343333a8e29582acd62758586a54e2167b09e1846b3c0f526c77c9ec3e8` |

Оба proof receipts привязаны к итоговым raw и AST hashes всех шести исходников. Все записанные файлы заканчиваются ровно одним newline. Временные scripts удалены.

**Передача родителю**

Остаются миграция фактических callers, включая все policy calls с `distribution_root=ROOT`, перенос существующего selection smoke, реальные assembled imports и существующие affected checks.

D01/D02/D03/D06/D09/D11 соблюдены в пределах среза: обязанности находятся в Core, зависимости конкретны, обратных вызовов монолита нет. Существующие identity/access/lifecycle/locking/recovery механизмы не изменены; затронутые требования R01–R12 не расширены новыми правилами.

Live fixtures, suite execution, installed/archive/connected проверки не выполнялись. Постоянные тесты, MCP endpoints/resource invocations, caches, permissions/framework additions, Git mutations, remote/infrastructure operations и вложенные агенты не создавались.