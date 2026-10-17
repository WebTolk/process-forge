# Финальный кандидат ProcessForge 1.2.0

Дата: 2026-10-17. Кандидат подготовлен для рассмотрения: документация согласована с принятыми изменениями, чистый архив и быстрые проверки прошли. Публичная публикация не выполнялась. Известные ограничения перечислены ниже.

## Точные исходники и архив

- Source commit: **25cf43b413f19cef1c0f4aa53ed66a5f535bd069**, tree **43b1c1fddc61852b2651580c994da38e775f7c1a**. Полный SHA прочитан из обеих веток origin/dev и gitverse/dev.
- [ZIP](../../tmp/pf120-final-docs-20261017/processforge-1.2.0-final-20261017.zip): 2532946 байт, 1308 записей.
- SHA256 ZIP: **827ef4329c8fa0f38c4d34f51cfe313592c7b1850edbc1d244cedc99e2782bf7**.
- [Sidecar](../../tmp/pf120-final-docs-20261017/processforge-1.2.0-final-20261017.manifest.json), SHA256 **fa5861c3c7af1703020beddc9335173d0a87d227304e21fbf22f9efbfed6a1f1**. Sidecar хранится рядом и не включён в ZIP.
- Native release-pack выполнен из чистого detached worktree. Исполняемый payload побайтно совпадает с квалифицированным dev source d5947ea6ab4a186dc4d9958aa19010a6dfc5c711 / ZIP 8103664d. Различаются ровно пять документов, inventory и generated Core manifest; состав архива сохранён.

## Документация и проверки

EN/RU release и migration notes описывают принятые SQLite journals и явный управляемый переход с сохранением старой истории; ограниченное повторное использование разбора YAML с текущими чтениями и проверками; Garage opt-in и native session lifecycle; разделение здоровья Runtime и результатов задач, частичные метрики и очистку собственного временного файла при ошибке публикации.
CHANGELOG объединяет принятый объём под 1.2.0 с датой кандидата 17 октября. Версии process/schema/startup contract и исторические капсулы не переписаны. Inventory изменён ровно для пяти документов; локальная проектная конфигурация сохранена.

| Проверка | Результат |
| --- | --- |
| Полный source suite d5947ea | Использован пригодный 274/274 PASS с проверкой неизменных исполняемых байтов; новый полный запуск не заявляется |
| Native release-check | PASS на чистом docs commit |
| Относительные ссылки | 23/23 PASS |
| Область правки и inventory | Пять документов + inventory; изменены ровно пять записей checksum |
| Native release-pack | PASS; чистые source/tree/provenance |
| Native release-archive-test | PASS за 91.946 с; quick, timeout_scale=1 |
| Извлечённый пакет | Обе CLI entrypoints и выбранные compile/schema/public-cleanliness/checksum/bootstrap/ingress/conversation/replay проверки PASS |
| Archive delta | Ровно семь записей, исполняемые байты прежние |
| Доставка source | Полный SHA совпал в обеих dev ветках |
| Исходный systems-check backlog | Выполнен один раз, native task/run completed; ссылочный report доставлен, doctors PASS |

Raw receipts: docs-checks.json, archive-identity.json, release-check.json, release-pack.json, release-archive-test.json, source-publication.json. Первичное описание implementation ошибочно называло 25 ссылок; фактический receipt и итог — 23. Review выполнил primary при subagent_policy.allow=false; отдельное независимое ревью именно этого diff не заявляется.

## Системная приёмка и скорость

[Системный отчёт](../pf120-prerelease-20261017/report.md) и [сводка](../pf120-prerelease-20261017/public-summary.json) сохранены в edf073e. Установленный Core, живой Runtime и фактически подключённый MCP приняты на dev d5947ea. Новый docs-only ZIP не устанавливался: исполняемый payload совпадает, но доставка новых заметок в установленную копию не заявляется.

CLI, медиана пяти повторов: версия 0.753 с, exact Work 0.882 с, ресурс 1.837 с, context-check 1.571 с. Actual MCP: exact Work 0.053 с, ресурс 2.087 с, поиск 2.102 с, context 14.675 с. Поверхности включают разные накладные расходы и не являются прямым A/B.

Runtime за 90 с: 7.239% всей мощности четырёх логических процессоров; отдельные окна 6.510–8.489%, рабочий набор около 150 MiB. До и после измерения ready, scheduler_alive, active_workers=0. Семь native diagnostics и две SQLite quick_check прошли.

## Открытые ограничения

- pf.context 14.675 с остаётся отдельным P2 performance follow-up для профилирования полного пути контекста.
- Metrics sessions/work/workers partial: budget, sessions также invalid/unreadable. Неизвестные значения не заменены нулями.
- Новый реальный native worker после последнего dev update не запускался; готовые source/archive/installed controls и прежний native worker учитываются с этой границей.
- Реальные Linux/macOS и полная матрица Python здесь не проверялись. Измерения относятся текущей нагрузке и не обещают универсального ускорения.
- Финальный ZIP имеет отдельную документационную квалификацию поверх 274/274, а не новый единый полный запуск финального дерева.

Tag v1.2.0 отсутствует, release assets не созданы; versioned update index сохранён с SHA256 14cf734e41e175fc3fdd3d8a276296e96b090d983ea1de9f6e5892f44d9d14f0. Установка, миграция и перезапуск Runtime/MCP не выполнялись. Перед публичной публикацией требуется решение по этому точному commit/ZIP/hash с учётом перечисленных ограничений.
