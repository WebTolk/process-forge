# Корни пакетов, платформы, обновления и контракты процессов

Primary run: `garage-p121-core-registries-20261018-move-existing-package-path-operatio`.
Assignment: `p121-core-registries-20261018-move-existing-package-path-operations-plat`.
Context: `p121-core-registries-20261018-move-existing-package-path-operations-plat-capsule`.

Реализация заморожена для независимой проверки. Манифест:
`.pf/artifacts/pf121-oop-core-registries-20261018/primary/product-manifest.json`.
Отчёт, полные native proof receipts, сравнение поведения и проверки находятся
в том же artifact-каталоге. Из монолита удалены 34 функции, осталось 771 определение.
Проверены 33 перенесённых алгоритма и удаление одного канонического wrapper,
94 случая паритета и девять существующих скриптов. Зафиксированы 16 продуктов.

В пределах исходников сохранены внешний контракт 1.2.0, прежние классы,
аннотации, публичная модель корня, aliases и порядок чтений/отказов. Остальные
слои приёмки и OOP-эпики открыты. Установка, запись версии, исполнение handoff,
жизненный цикл, блокировки и recovery не переносились. Новых MCP-ресурсов нет.

Окончательный статус независимого ревью фиксирует
`primary/review-acceptance.json`; SHA коммита и чтение обоих dev heads —
`primary/delivery/core-registries.json`. Native lifecycle receipts и root doctor
подтверждают завершение шести точных Work. Эти квитанции создаются по факту;
настоящая передача не подменяет их и не разрешает инфраструктурных действий.

GitVerse использует существующий GITVERSE_TOKEN через конфигурацию одного
процесса, credential helper отключён. Посторонние файлы и staged entries
сохраняются. ZIP и широкие release/install/Runtime проверки не требуются
для этого переноса исходников. Исходная архитектура полностью перечитывается
перед следующим срезом; исходный контекст проверяется файловым PF CLI.
