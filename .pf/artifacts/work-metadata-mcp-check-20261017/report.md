# Адаптация существующей MCP fixture

Дата: 2026-10-17 17:50:11 UTC. Результат: pass, supporting source-test slice.

В единственной fixture tools/smoke_garage_snapshot_read_composition.py локальная фабрика принимает необязательный keyword-only work_metadata=None. Когда зависимость передана, проверяется совпадение project_root ленивого read pass с root фабрики. Все прежние проверки session/project guards, порядка вызовов, результата pf.context, проекции знаний и очистки request scope сохранены. Новая продуктовая возможность, alias или runtime rule не добавлены.

До изменения исходный Git-код проходил все 8 тестов. После адаптации весь существующий smoke проходит: 8/8, exit 0. Изменённый callback также принимает прежний трёхаргументный вызов без metadata. Самопроверка diff: один параметр и проверка его bound root; исходные assertions не удалены и не ослаблены. Отдельный источник genuine factory failure исправлен первичной Work в её разрешённом composition.py, не в этом test scope.

Changed files: tools/smoke_garage_snapshot_read_composition.py и собственные план/report/handoff. Primary integration Work, владеющая checksums/processforge.sha256, обновила только строку данного теста для согласованного supporting commit: 1e47eb61b174ba059197326b5d5fd2ff70933b63bb8708b49809bb6636d1f9fb. Ни один второй writer не получал scope на checksum file.

Test plan/cases/report: existing complete GarageSnapshotTests suite, включая no-I/O composition, isolated import, current reads/same-size mtime/request cleanup, snapshot path changes, metadata fixture, guards и полный payload projection; 8 PASS. Review: pass. Scope respected. Main implementation и отдельные cold/warm measurements остаются у первичной Work.

Release-readiness decision: not_applicable, fixture/supporting source only. Delivery profile skipped with reason: нет пакета или установки, source/test change передаётся primary. Native doctors проверяют терминальное состояние. Own commit/push/readback follow project policy. Неприменимо к archive/installed/Runtime/actual connected-MCP acceptance.

Evolution: deferred optional Core dependencies должны учитываться в fixture, сохраняя проверки старых путей и всего публичного результата. Main write scope не расширялся; создана отдельная непересекающаяся Work. После закрытия не возобновлять.
