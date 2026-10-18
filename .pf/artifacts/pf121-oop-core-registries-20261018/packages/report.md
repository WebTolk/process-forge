# Отчёт packages: реализация и доказательства совместимости

Статус: **реализация завершена, ограниченные проверки PASS**. Проверка фактической сборки и переходы Work остаются основному исполнителю.

| Identity | Значение |
|---|---|
| project_id | `process-forge` |
| run_id | `garage-p121-core-registries-packages-extend-existing-projectpackagecatal` |
| assignment_id | `p121-core-registries-packages-extend-existing-projectpackagecatalogreade` |
| context_id | `p121-core-registries-packages-extend-existing-projectpackagecatalogreade-capsule` |

Точное `work-state` подтвердило `implementation`, контекст `valid`, readiness `ready`, отсутствие blockers и соответствие разрешённых действий/файлов подготовленному входу. Lifecycle самостоятельно не изменялся.

## Изменения

Единственный изменённый product-файл: `src/processforge_core/resources/project_packages.py`.

Существующий `ProjectPackageCatalogReader` расширен шестью методами, делегирующими существующему `WorkspacePathReferenceReader`:

| Legacy | Новый метод |
|---|---|
| `package_root_entries` | `root_entries` |
| `resolve_package_root` | `resolve_root` |
| `package_path_candidates` | `path_candidates` |
| `resolve_package_path` | `resolve_path` |
| `find_workplace_package_manifests` | `find_manifests` |
| `load_workplace_package_manifest` | `load_manifest` |

Правила registry/path/ID не скопированы. Новый приватный `_public_root` преобразует ровно семь полей `_PackageRootResolution` в существующий публичный `PackageRootResolution`: `root_id`, `original_path`, `resolved_path`, `status`, `warnings`, `fallback`, `entry`.

Преобразование сохраняет ссылки на поля, включая `warnings` и `entry`. В `find_manifests` локальная таблица соответствия identity сохраняет один публичный root для нескольких manifest одного канонического root. Таблица существует только при преобразовании готового списка; состояние между операциями не удерживается.

Прежний `root_from_entry` использует тот же converter. Других изменений прежней реализации нет.

## Доказательства AST, сигнатур и сохранности классов

Полные сравниваемые AST, результаты и исходные hashes находятся в `.pf/artifacts/pf121-oop-core-registries-20261018/packages/proof.json`.

**PASS, 6/6:** полный AST каждого канонического алгоритма сопоставлен с frozen legacy. Использованы только следующие нормализации:

- удаление аргумента `self`;
- `self.method` → соответствующее имя функции;
- `_PackageRootResolution` → `PackageRootResolution`;
- уже перенесённый legacy-вызов `_project_package_catalog_reader.root_from_entry` → `package_root_resolution_from_entry`.

До сравнения подтверждено совпадение AST frozen source со stored AST в `baseline-functions.json`. Guards, порядок операций, truthiness, сообщения, мутации и ветви ошибок не нормализовались.

**PASS, 6/6:** полный AST новых wrappers совпал с независимо заданными ожидаемыми телами делегирования и преобразования результатов. AST `_public_root` совпал с прежним семиполевым return-конструктором.

**PASS:** после удаления новых методов/приватного импорта и обратной подстановки единственного factoring весь прежний module AST совпал с frozen before-image. Тем самым сохранены:

- `from __future__ import annotations`;
- публичная модель, её поля, defaults, decorators и generated constructor;
- поля и constructor `ProjectPackageCatalogReader`;
- все прежние сигнатуры и аннотации;
- полные тела `workplace_roots`, `workplace_root_paths`, `candidates`, `index`, `dependencies`;
- всё остальное прежнее содержимое модуля.

**PASS, 6/6:** фактические bound `inspect.signature` и словари `__annotations__` совпали с frozen legacy-функциями. Сохранены следующие сигнатуры:

```python
root_entries(workplace_root: Path) -> list[dict[str, Any]]
resolve_root(workplace_root: Path, package_root_id: str | None = None, *, mode: str = "read") -> PackageRootResolution
path_candidates(root_path: Path, package_id: str) -> list[Path]
resolve_path(workplace_root: Path, package_id: str, package_root_id: str | None = None, *, mode: str = "read") -> tuple[PackageRootResolution, Path]
find_manifests(workplace_root: Path, package_id: str) -> list[tuple[PackageRootResolution, Path]]
load_manifest(workplace_root: Path, package_id: str, package_root_id: str | None = None, *, mode: str = "read") -> tuple[Path, dict[str, Any], PackageRootResolution]
```

Публичные имя, тип, repr и порядок семи полей результата сохранены.

## Синтетические проверки

Выполнено ровно пять сценариев в памяти с declared frozen AST и синтетическими документами/путями:

1. **PASS:** отсутствующий registry, fallback, публичная модель, defaults и порядок candidate paths.
2. **PASS:** truthy default, read/write refusal, неизвестные поля и identity `entry`/`warnings`.
3. **PASS:** неоднозначность manifest, порядок выбора, общий root-object для двух manifest и нормализация `resources`.
4. **PASS:** soft/strict YAML и распространение исходного экземпляра native `OSError`.
5. **PASS:** invalid IDs до registry reads, containment refusal и сохранение `ValueError` в cause.

Actual assembled imports, live fixtures и существующие suites не запускались. Эти проверки выполняет основной исполнитель.

## Scope и передача

Прочитаны объявленные архитектурные, Python и frozen dependency inputs, brief, исходные OOP-02/03/05 и Core `AGENTS.md`. Использована Serena; итоговый Git diff просмотрен read-only.

Сохранены применимые D01/D02/D03/D06/D09/D11: owning Core delegation, конкретные зависимости и отсутствие обратного пути в монолит. Новых правил доступа, permissions, инфраструктуры, DI, Kernel, plugin framework или межоперационного кэша нет. Actual package mutation не добавлена.

Evidence: `packages/proof.json`; журнал: `packages/log.md` внутри выделенного artifact-каталога. Scratch verifier удалён; постоянные тесты не добавлены. Все оставшиеся записанные файлы завершаются ровно одним newline.

Основному исполнителю передаются actual assembly/import verification, live fixtures, existing affected checks, регистрация evidence и native transitions.

## Итоговые raw SHA-256

`src/processforge_core/resources/project_packages.py`

```text
87da19314b5acd8ca4ae9df0554205165b224e45a27742633a4e8c241ef29d03
```

`packages/proof.json`

```text
d53598172d18c48430ddd86c650d6527c3692e0487d3a054c9f0bb72bd52b333
```

`packages/log.md`

```text
ac0a9fb30b3fd45602f81678ff4905ad0b03ff49c5963cd71dc2b345da6c2b77
```