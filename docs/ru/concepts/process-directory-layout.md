# Раскладка каталога процессов

Process definition определяется по `id`; путь к файлу является местом хранения, а не идентичностью процесса.

ProcessForge использует три process roots:

- `processes/core/`: встроенные процессы ProcessForge, поставляемые вместе с дистрибутивом.
- `processes/user/`: процессы, созданные локально через process authoring или вручную.
- `processes/custom/`: импортированные, мигрированные, brownfield-нормализованные и другие нестандартные локальные процессы.

`processes/user/` является стандартной целью записи для `process-create` и `process-authoring-apply`. Запись в `processes/core/` считается maintainer-действием и требует явного core-флага.

Resolver ищет user/custom roots перед core, сохраняет `process_id` при переносе файла и показывает `origin`, `root`, `path` и catalog role в `process-list`. Старые плоские файлы `processes/*.yaml` поддерживаются только как миграционный fallback и дают warning.

Публичный release archive включает `processes/core/**` и только placeholder-файлы в `processes/user/` и `processes/custom/`. Реальные user/custom process definitions являются приватным состоянием рабочего места или проекта и не попадают в публичный дистрибутив.

Эта раскладка поддерживает три основных сценария:

- Greenfield first workspace: новый пользователь стартует от встроенных процессов PF и создаёт свои процессы в `processes/user/`.
- Studio workstation provisioning: чистая машина устанавливает уже отлаженные пакеты и использует поставляемые core-процессы без ручного пересоздания.
- Brownfield normalization: существующие AGENTS.md, сниппеты, skill packs и разрозненные документы импортируются в `processes/custom/` или формализуются как user-процессы.
