# Оркестрация уточнённой области

Дата: 2026-10-17. План и исходные исследования сохранены в `orchestration.md`; predecessor закрыт через точный `pf.work.cancel` без изменения capsule или product files. Handoff: `.pf/handoffs/hook-sqlite-migration-20261017.md`.

Текущий run: `garage-hook-sqlite-implementation-20261017-migrate-project-hook-event-jo`.
Assignment: `hook-sqlite-implementation-20261017-migrate-project-hook-event-journals`.
Capsule: `hook-sqlite-implementation-20261017-migrate-project-hook-event-journals-capsule`.
Checksum: `sha256:6fe6e4d157026bd12a62ea2c27d5d85c4dd5444b72608edf2a53d70a63d5083c`.

Assignment, capsule и Work state прочитаны; snapshot fresh, validation valid, readiness ready. Точные selectors сохранены для каждого Work-вызова. Дополнительно разрешены существующие configuration CLI/parser, configuration smoke и configuration template. Чужой smoke по-прежнему исключён. Subagents запрещены capsule.

Режим: source implementation с исследованием, domain и architecture до product edits, затем focused assurance и commit/dual-push. Прямое поручение пользователя авторизует SQLite, настройки и мигратор. Установленный Core/Runtime/MCP не изменяются этим Work. Проверка устройства 1.2.0 отложена.

Уточнение пользователя: журнал проекта мыслится как история работы и решений (оператор, основной агент, субагенты, shell-workers); переходы стадий и создание задач являются уровнем подробности этого представления и не всегда нужны. Журналирование должно быть отключаемым; рабочие состояния, доставка и необходимые доказательства должны иметь собственные источники истины. Проверяется фактическая зависимость текущего PF от журнала, прежде чем выбрать реализацию.

Дальнейший план: intake -> inventory источников/читателей и config -> domain событий/истории/обязательного состояния -> SQLite schema, override/reload и migrator architecture -> implementation -> concurrency/migration/config/recovery checks -> delivery/evolve. Используются уже выполненные исследования и разрешённые локальные Python docs; инфраструктура и реальные журналы не переключаются в source-проверках.
