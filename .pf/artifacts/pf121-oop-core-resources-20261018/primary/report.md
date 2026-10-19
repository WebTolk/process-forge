# Ресурсы, диагностика пакетов и worker prompt

Реализация и ограниченная проверка завершены. Для независимого ревью закреплены
18 продуктов на базе 5bb90b6fe072c3c57f8ec5c27700f3c87025ea82.

ResourceRecordService владеет прежними defaults, выбором зарегистрированного
корня, публичным path_ref и нормализацией. Точный HEAVY_RESOURCE_KINDS перенесён
в тот же модуль. Готовые ContextContractInputs, WorkspacePathReferenceReader
и ResourceSnapshotRules переиспользуются. Порядок реестров, первое совпадение,
граница префикса/регистр, URL precedence, private path hiding, shallow copy,
borrowed values, unknown fields и native failures сохранены. register_private_path
по-прежнему не используется и не создаёт регистрацию или запись.

KnowledgePackageValidationService владеет полным прежним doctor пакета через
конкретные catalog/document/index/record/policy owners. Первоначальное чтение
манифеста и отдельное doctor_yaml сохранены; warnings, schema refusal, resources,
index/privacy/navigation/dependencies/policy наблюдаются в прежнем порядке.
KnowledgeResourceIndexService владеет путём индекса, path_ref findings и индексами
ресурсов проекта. Ранний возврат package.yaml, канонические ID/containment rules,
шесть registry mappings, package-only/external exemptions, skips и необязательный
локальный индекс сохранены. Буквальный path_is_relative_to добавлен в common.paths;
прежний модуль совпадает полным AST и raw prefix. Ловится только ValueError.

WorkerAssignmentService владеет строгим полным чтением Assignment и прежним
92-строчным prompt. Используются готовые WorkPaths, ProjectMetadataReader,
ContextContractInputs и YamlDocumentReader.read. Сохранены missing-file/SystemExit,
strict YAML refusal, unknown fields, safe ID/путь/чтение, prepared-input branches,
все English literals, workspace counts, output/report/subagent fields и newline.
Проекционное чтение метаданных не подменяет полный документ. Конструкторы
холодные; roots и документы не удерживаются между операциями.

Все шесть фактических потребителей чтения Assignment переведены вместе: Host
и пять existing smoke scripts. Заменены ровно 11 call targets и необходимые
imports/cold instances после существующего bootstrap. Полный AST и raw bytes
подтверждают сохранность остальных guards, fixtures, assertions, signatures
и сторонних helpers. Основной исполнитель проверил эти границы независимо.

Четыре native-вклада приняты по фактическим отчётам и текущим raw hashes.
Полные 12 алгоритмов, сигнатуры, future/string annotations, константа и прежние
владельцы подтверждены. Двадцать полезных stub-сценариев сохранены без повторов.
Primary получил 98 сравнений, включая 12 карт аннотаций, шесть native exceptions,
реальные корни/реестры/манифесты/index/navigation/dependency ветви, shallow aliases,
строгое чтение неизвестных полей, same-size/same-mtime изменение и точные полные
prompt bytes. Есть явные ожидания, что положительные doctor/index случаи прошли
до требуемых ветвей. Прямой/скопированный Core импортируется без Main/Host.

Assembled QA обнаружила прежний контракт импорта Host до Core bootstrap:
eager canonical YAML imports прежнего serializer среза и новый reader import
требовали уже доступного src. Первое prompts Work отменено точно; неизменные
отчёт и proof сохранены. Governed prompts-final successor изменил только
расположение канонических импортов/холодной сборки в существующих операциях
Host/Service. Остальные алгоритмы и пять consumers сохранены побайтово.
Прямого или косвенного импорта Main и нового bootstrap нет. Два изолированных
порядка импорта Runtime modules при доступном только tools подтвердили отсутствие
загрузки Main/Core и запуска сервиса. Все 98 Core сравнений и два ранее успешных
скрипта сохранены; bootstrap-resolution.json связывает окончательные исходники
с неизменными алгоритмами и новыми проверками import order.

Полный поиск имён также обнаружил динамические mock targets в recovery и
governance scripts и прямой from-import проверки локального индекса. Отдельный
governed prompts-bound successor изменил только эти три consumer bindings:
patch.object теперь направлен на канонический класс, pf-вызов и прямой импорт —
на фактические Core owners. Все assertions/fixtures сохранены, семь остальных
продуктов побайтово прежние. Старые completed назначения отменены точно, капсулы
и доказательства неизменны; никакого legacy alias или ослабления теста нет.
Итоговое покрытие — восемь consumer модулей. Три успешных скрипта, 98 сравнений
и оба import orders сохранены; consumer-binding-resolution.json связывает
оставшиеся проверки с окончательными исходниками и исходной ошибкой wiring.

Пройдены девять existing source scripts: continuation work, expected report
containment, prepared execution context, prepared execution recovery, process
run task batch, resource indexing policy acceptance, codex worker governance,
project local package index detection и docs current code contract.
Успешные scripts не повторялись; prepared context после раннего отказа импорта
и recovery после ошибки mock target завершены повторными попытками, остальные
ещё не выполненные запущены штатно.
Affected recovery script проверяет изменённое чтение исходников; это не Runtime
qualification. Host импортируется потребителями без запуска реального сервиса.
Широкие release/archive/install/Runtime/connected-host и ZIP проверки не выполнялись.

Удалены 12 функций и один набор данных Main. Полный AST 718 оставшихся определений
и остальных узлов содержит только запланированные импорты, композиции и вызовы.
EN/RU ownership обновлён. Inventory меняет 13 строк, добавляет четыре и сохраняет
1360 остальных; три известных посторонних расхождения не затронуты.

Приёмка source-only, внешний контракт 1.2.0 сохранён, новых возможностей нет.
OOP-эпики открыты. После ревью — один selected commit в оба dev remote с полным
SHA readback, штатное завершение шести Work/root doctor и полное перечитывание
девяти архитектурных входов. GitVerse использует существующий токен, credential
helper/tracing отключены. Постороннее dirty/staged состояние сохраняется.
