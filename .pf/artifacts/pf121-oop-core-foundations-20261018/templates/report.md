# Отчёт templates

Статус: реализация в назначенной области завершена; ограниченная проверка пройдена.

Run: `garage-p121-core-foundations-templates-create-project-templates-py-templ`  
Assignment: `p121-core-foundations-templates-create-project-templates-py-templatecata`  
Context: `p121-core-foundations-templates-create-project-templates-py-templatecata-capsule`

SOURCE CLI подтвердил этап `implementation`, валидный контекст и readiness `ready` без blockers. Проверены 30 закреплённых входов.

Создан `src/processforge_core/project/templates.py`: `TemplateCatalogService(distribution_root: Path)` с методами `resolve_root` и `manifest`. Конструктор собирает конкретные зависимости без I/O. WorkspacePathReferenceReader получает фактический workplace root при операции; существующие алгоритмы разрешения путей переиспользованы.

Сохранены fallback `${PF_TEMPLATES}`, upsert перед проверкой выбранного ID в write mode, выбор available/first, mkdir только при `mode == "write"`, приоритет candidate и возврат по первой подходящей registry entry. Новые проверки путей и правила package roots не добавлены.

Проверки:

- Полные нормализованные AST обоих алгоритмов, сигнатуры и строки аннотаций совпадают с оригиналами.
- Компиляция выполнена без импорта продуктовых модулей.
- Raw bytes и AST 15 неизменяемых зависимостей совпадают с frozen inputs.
- Все пять синтетических сценариев прошли: read fallback; upsert до ошибки неизвестного ID; available selection с native mkdir error/cause; candidate short-circuit; повторное чтение registry и остановка на первом отсутствующем manifest.
- Итоговый `proof.json` прочитан и проверен. Файлы заканчиваются ровно одним newline.

Итоговые raw SHA256:

| Файл | SHA256 |
| --- | --- |
| `src/processforge_core/project/templates.py` | `86321caa8deb9199e6579ba9cbff3b03fc27a4a1c6f102a358c6d7c3cb964285` |
| `templates/proof.json` | `792dd1adef85e6ea3789ba23530b594dc39c51bb54e6bfcbc3e800f3f3b50caa` |
| `templates/verify.py` | `2a6b8c057cff3170cace3d170197ae5c1ce4f345b8dc69dedead1ee89d9a48e2` |
| `templates/activity.md` | `a5e3e1478c9af71e5b2e2b023ee7fdc3b9e789085da5e5dcacc439905508c7a1` |

Пути `templates/*` указаны относительно `.pf/artifacts/pf121-oop-core-foundations-20261018/`.

Передача основному исполнителю: проверить actual Core composition/imports, реальные операции в bounded scratch, миграцию consumers и affected scripts. Изменяемые peer bodies не читались; проверка сохранности `common.values` принадлежит registry worker. Фактические workplace writes, изменения Main, docs/inventory, Git, инфраструктуры и lifecycle не выполнялись.
