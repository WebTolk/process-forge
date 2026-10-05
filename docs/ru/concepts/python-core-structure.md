# Структура Python-Ядра

Ядро развивается поэтапно. `tools/processforge.py` остаётся действующим legacy facade, а не удалённым кодом. CLI, MCP, hooks и aliases bootstrap сохраняются.

## Текущие Обязанности

| Модуль | Обязанность |
| --- | --- |
| `src/processforge_core/garage.py` | Сервисы проекта, контекста и чтения текущей работы, включая `CurrentWorkService`. |
| `src/processforge_core/process_execution.py`, `continuation.py` | Управляемый lifecycle, выбор работы, pinned execution, evidence, завершение и восстановление. |
| `src/processforge_core/document_store.py`, `work_inventory.py` | Чтение YAML и актуальный отсортированный обход без общего изменяемого кеша документов. |
| `src/processforge_core/ports.py` | Внутренние типизированные зависимости; первый порт содержит только поиск `.pf` и чтение документа. |
| `src/processforge_core/composition.py` | Явная фабрика сервиса чтения и адаптер двух операций legacy-модуля. |
| `src/processforge_core/bootstrap.py` | Существующая сборка runtime-модулей и ленивый доступ к фабрике чтения. |
| `tools/processforge.py`, `tools/pf_runtime/` | Legacy CLI facade, транспортные адаптеры, host и provider policies. |

`build_current_work_service(project_root, port)` создаёт прежний сервис с любой структурно подходящей зависимостью, без загрузки CLI и без ввода-вывода при сборке. `RuntimeBootstrap.current_work_service(project_root)` использует уже загруженное ядро через `LegacyWorkReadAdapter`. Глобальный реестр сервисов, общий кеш и DI-контейнер не вводятся.

Конструктор `CurrentWorkService(project_root, core)` и путь класса сохранены. Порядок обхода, fallback отсутствующего assignment, исключение bootstrap placeholders, форма summary и обработка ошибок не меняются. Прежним потребителям не требуется немедленная миграция.

## Границы

Порты и фабрика пока внутренние, предварительные интерфейсы, а не расширение стабильного публичного API пакета. `Protocol` описывает зависимость для проверки типов, но не выдаёт права и не проверяет grants. Порт чтения не содержит переходов или записи состояния.

Остальные сервисы ещё зависят от legacy core. Целевая структура: предметные правила, прикладные сервисы, инфраструктурные адаптеры и тонкие транспорты с явной сборкой. Полное выделение этих слоёв ещё не выполнено. Исторические форматы, pinned capsules, защитные отказы и доверенные provider boundaries должны сохраняться.

`tools/smoke_core_read_composition.py` проверяет прежнее поведение, подмену порта, поля bootstrap, делегирование и изолированный пакет в структуре установки без CLI. Такая fixture не является приёмкой установленного Core или подключённого хоста. Проверки исходников, архива, установки и connected host разделены.
