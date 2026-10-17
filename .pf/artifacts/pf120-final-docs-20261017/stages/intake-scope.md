# Точная граница правки
5документов: CHANGELOG, EN/RU1.2.0 release и migration; шестойфайл — штатный checksum inventory. Никакой логики CLI/MCP/Runtime, схем, VERSION, egress, policy или stable feed не меняем.
Acceptance: новые release notes отражают SQLite/YAML/Garage/Runtime; миграция требует управляемой остановки старых journal writers/backup и явного migrator apply, с сохранением legacy данных; повтор already-qualified update не предлагается. Новые hashes соответствуют5docs. Clean final ZIP и native integrity/quick результат привязаны точному source commit; installed/Runtime/MCP evidence остаётся на d5947ea.
Будущий публичный tag/assets/feed остаётся решением пользователя. Предрелизная подготовка и push dev уже входят в поручение.
