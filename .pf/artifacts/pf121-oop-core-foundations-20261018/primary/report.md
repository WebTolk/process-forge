# Реестры, шаблоны и проверки платформ

Реализация и ограниченная проверка завершены; для независимого ревью закреплены
десять продуктов на базе d935e9bc981c85c4179eb91062c92eabe29ea92f.

WorkplaceRegistryWriter владеет полным прежним upsert_registry_entry: двенадцатью
registry/schema mappings, guards, проверкой схем и причиной SystemExit, errors[:8],
UUID staging рядом с назначением, записью, os.replace и finally exists/unlink.
Порядок ошибок и приоритет отказа cleanup сохранены. Новых locks, retries,
fsync или замен алгоритма атомарной записи нет. upsert_resource буквально
добавлен в common.values; прежний модуль совпадает полным AST и raw prefix.
Первое совпадение ID, тот же список, borrowed entry и строки added/updated точны.

TemplateCatalogService владеет прежним выбором корня и поиском манифеста через
конкретные WorkplaceRegistryWriter и WorkspacePathReferenceReader с фактическим
workplace. Read остаётся без записи. Write сохраняет fallback upsert ДО проверки
выбранного ID и прежний mkdir. Candidate-first и первая registry entry с отсутствующим
путём сохраняют короткое завершение. Новых path/containment правил не вводилось.

PlatformContractValidationService владеет прежними семантическими checks через
существующие contract/policy/resolution/selection/package owners и TemplateCatalogService.
Сохранены все сообщения и CLI hints, порядок проверок, повторные index/manifest
чтения, optional/required/inherited resources, missing/cycle/stack и falsey fallback.
Чистые policy_entries/policy_id_matches расположены в common.policies; остальные
Main callers используют эти же функции, без совместимых legacy aliases.

PlatformDependencyPreflightService владеет прежним preflight и прямым чтением ID
workplace реестров. Сохранены порядок и дубликаты missing resources, truthiness
manifests, проверка template is None, безусловные tools/MCP reads и исходный SystemExit.
Все конструкторы холодные; документы не кэшируются, root передаётся на операцию.

Все четыре native-вклада прочитаны и приняты по итоговым raw SHA. Полные девять
алгоритмов, сигнатуры, строковые аннотации, данные и readonly owners подтверждены.
Двадцать ограниченных stub-сценариев включают schema cause, частичную stage write,
replace/cleanup error precedence, повторные наблюдения и native regex/KeyError.
Успешные сценарии не повторялись. Конкретные Core APIs проверены до admission;
immutable before-images зависимостей исключили конфликт peer source pins.

Primary подтвердил 88 сравнений: девять карт аннотаций, shared policy/list identity,
реальные scratch upsert/schema/corrupt-registry/replace-failure ветви, read/write
fallback и unknown template ID с прежними эффектами, реальные semantic/required/
recommended/cycle checks, package/template/tool/MCP aliases и прямой/скопированный
Core без Main/Host. Двенадцать native exceptions совпали. Явные ожидания доказывают,
что положительные случаи вернули данные, а отказы сохранили исходные файлы и
не оставили staging. Все данные проверок находятся только в собственном scratch.

Пройдены четыре существующих скрипта: remediation registry safety, remediation
platform layout strict, platform create include levels и docs current code contract.
Широкие release/recovery/archive/install/Runtime/connected-host и ZIP проверки не
выполнялись. Сервис или инфраструктура не запускались.

Из монолита удалено девять определений. Полный AST 730 оставшихся определений
содержит только объявленные импорты, четыре композиции и миграцию вызовов;
фактических внешних source consumers выбранных старых функций не обнаружено.
EN/RU ownership обновлён. Inventory меняет четыре строки, добавляет пять,
сохраняет 1364 остальных и три известных посторонних расхождения.

Приёмка source-only, внешний контракт 1.2.0 сохранён, нового поведения нет.
OOP-эпики открыты. После ревью следуют один коммит в оба dev remote с полным SHA
readback, штатное завершение шести Work/root doctor и полное перечитывание девяти
исходных архитектурных документов. GitVerse — существующий токен без credential
helper и verbose tracing. Посторонние dirty/staged изменения сохраняются.
