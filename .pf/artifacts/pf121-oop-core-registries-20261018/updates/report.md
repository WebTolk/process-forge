# Отчёт updates

Статус: **реализация выполнена; локальное доказательство PASS**. Интеграционная assurance остаётся родительскому исполнителю.

## Identity и полномочия

- Run: `garage-p121-core-registries-updates-create-updateregistryreader-distribu`.
- Assignment: `p121-core-registries-updates-create-updateregistryreader-distribution-ro`, attempt 1.
- Context: `p121-core-registries-updates-create-updateregistryreader-distribution-ro-capsule`.
- Context checksum: `sha256:cbe4af735492cdb9896bbc69dbe9a1ced151f1edb77e2d0427c26cb126d0a28a`.

Exact source CLI Work state подтвердил `implementation`, `valid`, `ready`, отсутствие blockers и наличие implementation-plan. Новые Work, переходы lifecycle и пересборка контекста не выполнялись.

## Изменения

Создан `src/processforge_core/maintenance/registries.py` с `UpdateRegistryReader(distribution_root: Path)`:

| Исходная функция | Новый метод |
|---|---|
| `update_entity_manifest_records` | `entities` |
| `update_site_overrides` | `overrides` |
| `installed_subjects_by_key` | `installed_subjects` |
| `update_install_path` | `install_path` |

Используются конкретные `UpdateDocumentReader`, `ProjectPackageCatalogReader.workplace_root_paths`, `WorkspacePathReferenceReader`, `UpdateSitePolicy`, канонические `UPDATE_SUBJECT_TYPES` и `safe_id`. Конструктор собирает зависимости без I/O; workplace передаётся каждой операции.

В существующий `UpdateDocumentReader` добавлены ровно `runtime_root`, `candidates_path`, `notifications_path`.

Actual installation, timestamped installed-version writing и update lifecycle оставлены legacy. Clock, atomic-write, caches и новые permissions не добавлены.

## Доказательство сохранения

`updates/proof.py` и `updates/proof.json` содержат воспроизводимую проверку:

- Все **7/7** полных AST совпали с frozen baseline после нормализации только имени метода, `self`, concrete owner references и вызовов operation-bound path reader.
- Все **7/7** runtime signatures без добавленного `self` и словари строковых `__annotations__` совпали.
- После удаления ровно трёх добавленных методов весь AST `documents.py` совпал с frozen before-image: сохранены imports, данные, constructor, fields, docstrings и все **14 прежних методов**.
- Сохранён `from __future__ import annotations`; оба модуля компилируются без исполнения imports.
- Сохранены порядок glob groups, package-only `seen`, фильтры/defaults, unknown fields и ссылки на исходные mappings, last-wins keys, truthiness/alias priority overrides и порядок install override → current installed record → fallback.
- Native ошибки не перехватываются новыми обработчиками; порядок guards, reads и mutations сохранён нормализованным AST.
- `git diff --check` завершился успешно. Все записанные файлы заканчиваются ровно одним newline.

Сигнатуры новых методов после исключения `self`:

```python
entities(workplace_root: Path) -> list[dict[str, Any]]
overrides(workplace_root: Path) -> dict[str, dict[str, Any]]
installed_subjects(workplace_root: Path) -> dict[tuple[str, str], dict[str, Any]]
install_path(workplace_root: Path, candidate: dict[str, Any]) -> Path
runtime_root(workplace_root: Path) -> Path
candidates_path(workplace_root: Path) -> Path
notifications_path(workplace_root: Path) -> Path
```

## Синтетические проверки

Все пять сценариев прошли без assembled Core imports и live fixtures:

1. Constructor wiring, operation-bound references и три пути runtime.
2. Порядок discovery/groups, package-only deduplication, filtering/defaults и data aliases.
3. Overrides: alias/truthiness priority, malformed items, last-wins и identity.
4. Installed subjects: фильтрация типов, пустые строковые ключи, last-wins aliases и повторное актуальное чтение.
5. Install path: override/current-record/fallback, `safe_id` и сохранение identity/cause исключения.

## Входы и архитектурные границы

Прочитаны подготовленные ADR/domain/direction, clarification, migration contract, progressive decision, OOP-02/03/05, brief, полный baseline, Core AGENTS, Python material/provenance и frozen dependency inputs. Внешние документационные ресурсы не открывались.

D01/D02/D03/D06/D09/D11 соблюдены в пределах среза: реализация принадлежит Core, зависимости конкретны, транспорта и обратных вызовов монолита нет. Затронутые R01–R12 сохранены; новые правила identity/access/lifecycle не вводились. Serena/IDE недоступны, применено чтение точных разрешённых файлов.

## Финальные raw SHA-256

| Файл | SHA-256 |
|---|---|
| `src/processforge_core/maintenance/registries.py` | `9318ce83e41add134d286022aa4f3502b56ebeffad788b03ebc2f77d9c6249f3` |
| `src/processforge_core/maintenance/documents.py` | `70ca9ad829459fb887f3682f569defd63d9ed08b36547cb0c675e6deb40b4b63` |
| `updates/proof.py` | `a72871eba560f6119e14a13cd8de03232ebcc5bd92c7ef73642b9101a6a529a2` |
| `updates/proof.json` | `511f22fc9d15b5afe989eea2e327ea88cfd4bf60a9e1087e05d8e3bbd94f32a0` |

Пути `updates/*` относятся к `.pf/artifacts/pf121-oop-core-registries-20261018/`. Журнал — `updates/log.md`.

Родителю остаются consumer migration, actual assembled imports, live fixtures, existing affected checks и native evidence/transitions. Source/package/archive/installed/Runtime/connected-host квалификация этим отчётом не заявляется.