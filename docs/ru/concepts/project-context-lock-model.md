# Lock-модель project context

`context_requirements` в `.pf/process-forge.yaml` - это декларация зависимостей проекта. В ней проект описывает нужные knowledge packages, resources, templates, tools и platform contracts.

`.pf/contexts/project-context.snapshot.yaml` - это resolved lock-файл. Он хранит сгенерированный snapshot id, содержимое, пригодное для checksum, resolved resource instances, generations, fingerprints и уровень воспроизводимости. Старые поколения лежат в `.pf/contexts/project-context.snapshots/`.

## Режимы ресурсов

- `multi_version`: ресурс закрепляется версией и instance id. Новая версия даёт `fresh_with_updates`; исчезновение закреплённой версии даёт `broken`.
- `single_current`: доступен только текущий экземпляр. Изменение fingerprint делает snapshot `stale`.
- `rolling_index`: текущая генерация меняется со временем. Изменение generation или fingerprint делает snapshot `stale`.
- `external_live`: воспроизводимость best effort. Freshness зависит от записанного external fingerprint или generation.

## Freshness

`project-context-check` возвращает:

- `fresh`: текущий snapshot всё ещё соответствует requirements и resolved resources.
- `fresh_with_updates`: закреплённые ресурсы доступны, но есть новые совместимые версии.
- `stale`: нужен refresh, потому что rolling/current resources изменились или update пометил snapshot stale.
- `broken`: закреплённый ресурс или обязательный источник отсутствует.

`context_policy` управляет стартом сессии: по умолчанию `fresh` продолжает работу, `fresh_with_updates` уведомляет, `stale` просит оператора, `broken` блокирует.

## Capsules

Assignment capsules закрепляют snapshot id и `sha256` checksum на момент создания capsule. `project-context-refresh` создаёт новое поколение для будущих capsules и не переписывает существующие capsules.

