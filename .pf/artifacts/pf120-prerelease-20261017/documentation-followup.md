# Документационный follow-up для кандидата 1.2.0

Найдено проверкой17октября: notes EN/RU отрицают уже принятый межзапросный YAML parse cache и не описывают SQLite journal cutover, Garage hook policy и новые правила operational health/publication. CHANGELOG держит эти принятые изменения в Unreleased при установленнойVERSION1.2.0.

Точная правка:
- CHANGELOG.md: перенести4 Unreleased пункта в1.2.0, добавить SQLite journals/migrator/logging и дату текущего кандидата17октября, сохранить Unreleased как следующую границу.
- docs/releases/1.2.0.md и docs/ru/releases/1.2.0.md: заменить ложное «cache not accepted» точным описанием bounded64MiB/4096 process-local parse reuse с текущими чтениями/проверками; добавить ссылки SQLite/Garage/runtime health/publication; оставить OOP и performance/portability ограничения честными.
- docs/releases/1.2.0-migration.md и RU: явный controlled SQLite cutover с сохранением legacy journals и backup, мигратор по ссылке; Core update не запускает мигратор и не перезагружает MCP автоматически; Garage opt-in/inheritance и logging независимы от Work; current context/capsules сохраняются.
- checksums/processforge.sha256: штатно обновить по шести исходным файлам; прочие продуктовые байты не менять.

Доставка: новый отдельный bounded Work с write_product только этим6файлам и собственным artifacts/tmp. Clean detached candidate из docs commit; native release-pack и release-archive-test quick с обычными исходными timeout без увеличения. Полный274/274 reuse только для неизменного исполняемого дерева d5947ea. Сверить ZIP member differences именно5docs+inventory+generated manifest, source/archive identity и собственные public checks.
Не устанавливать повторно, не мигрировать устройство, не перезапускать Runtime/MCP. Текущий installed/Runtime/MCP относится d5947ea; doc-only final archive — новая отдельная доказательная граница. Не создавать v1.2.0 tag/assets и не менять stable feed.
