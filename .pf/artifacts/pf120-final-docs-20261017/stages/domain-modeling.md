# Контракты документации
Core update, миграция проектных журналов, запуск Runtime и фактическое переподключение MCP — разные действия/слои. Notes не дают разрешения повторять apply или перезапускать сервисы.
SQLite WAL локален; сохранение legacy journals не заменяет live backup API. Migrator preview без apply не создаёт project DB; незавершённый импорт блокирует обычную работу до подтверждённого завершения.
YAML reuse process-local и ограничен оценочным retained объёмом; чтение текущих байтов, права и validation остаются live. Это не RSS-limit, новая служба либо SQL migration Work YAML.
Garage opt-in не отменяет Forge gatekeeper; logging flags независимы от Work/chat. Runtime health отделена от task outcomes и partial metrics. Публикация убирает свой временный файл при ошибке, сохраняя destination/исключение; kill/cleanup denial остаются ограничением.
Квалифицированный старый код и новые документационные байты учитываем раздельно.
