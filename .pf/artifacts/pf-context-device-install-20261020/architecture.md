# Решение о native delivery

## architecture / implementation-plan
Использовать существующий native core-update apply --confirm из принятого чистого
checkout. Перед apply повторно сверить SHA пакета, installed manifest и static
protection baselines. Не использовать force-local-modifications, ручное копирование,
перезапуск или новый package build. Исполнение apply — один раз, с новым namespace.
После apply проверить status/incomplete, весь installed owned manifest, реальные
source module hashes, backup preimages, protected/unowned/Workplace/source guards,
installed project-context-check и doctor-workplace. Repair допускается только как
read-only inspect. При неясном исходе читать status/journal, не повторять apply.

## automation-readiness / architecture-approved
Native plan без blockers и local conflicts; safe backups входят в штатный updater.
Публичные payloads и новая логика не проектируются. Код принят/проверен в source
Work; новый writer владеет только артефактами установки. User сам restart session.
Приёмка фактическим connected MCP после его restart будет отдельным наблюдением.
