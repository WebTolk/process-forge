# План будущей реализации

Статус: planning_only. Код писать после отдельного поручения и новой точно ограниченной Work. Текущая Work не переиспользуется после завершения.

1. Зафиксировать исходный корпус и прежние результаты в существующих проверках Work summary/catalog/selection; сохранить последовательность отказов и подставляемые reader seams. При реализации включить архитектуру, diagnostic report, clarification, domain-map и refactoring-plan в required_sources.
2. В области work выделить project-bound получение компактных метаданных и immutable request-снимок. Использовать текущие WorkInventory/YamlDocumentReader/safe_load_fields и существующий content/parser-policy cache. Один field set на Run, один на Assignment. Не дублировать YAML-парсер, не возвращать усечённые документы из полных методов.
3. Подключить CurrentWorkService и WorkRecordCatalogService к общему явному read pass через composition. Существующие WorkProjectionPolicy и WorkSelectionService остаются владельцами разных правил. Для completion journal использовать полные текущие документы и нынешнего валидатора.
4. Подключить общий проход к сборке pf.context в MCP и к существующим Core consumer paths CLI/Runtime, где реально нужен каталог. В transport не переносить алгоритмы. Exact canonical selectors продолжают обходиться без полного inventory.
5. Read-after-write обеспечивать новым явным read pass после записи. Не требовать изменения всех native/legacy/external writers и нового межпроцессного invalidation protocol.
6. Выполнить сценарии архитектуры в существующих проверках и только необходимые дополнительные regression cases. После завершения реализации — review, затем пять сопоставимых холодных/тёплых измерений на неизменном корпусе. Проверить parse counters, memory, eviction, число обходов и наличие текущих файловых чтений.
7. Обновить относящиеся EN/RU docs и checksums. Source, archive, installed, Runtime и actual connected MCP квалифицировать раздельно в разрешённых scopes. Не устанавливать и не перезапускать службы ради этой архитектурной Work.

Предполагаемая область файлов: src/processforge_core/work/records.py, inventory.py, record_catalog.py и небольшой новый metadata-модуль при необходимости; composition.py; минимальный integration path pf_runtime/mcp_server.py. Общий reader/cache менять только при выявленной необходимости, с сохранением его существующих гарантий. Конкретный список определяется перед admission реализации, не выдаётся этим документом как grant.

Один автор на общую связную область. Ревью и тестирование реализации после её завершения. Отдельная схема БД, daemon, public MCP tool, миграция YAML и обновление устройства отсутствуют в плане первого среза.
