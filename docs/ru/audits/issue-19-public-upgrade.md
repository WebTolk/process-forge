# Обновление public 1.2.0: файлы Core и готовность проекта

> Исторические результаты. Решение владельца от 17.11.2026 отменяет приведённые ниже предпосылки исторического менеджера/cold exclusion и автоматической миграции. Текущее поведение описано в [execution storage](../concepts/execution-storage.md) и [обслуживании журналов](../concepts/sqlite-journal-maintenance.md). Старые owned startup templates обрабатываются по manifest, независимо от версии продукта.

Внешний updater Core принимает три публичных startup template из установленного ownership manifest версии 1.2.0: .pf/AGENTS.md, .pf/hooks.yaml и .pf/process-forge.yaml. Перед удалением файлов, которыми новая версия больше не владеет, сохраняются реальные preimages либо факт отсутствия. Исключение относится только к установленному manifest точной версии 1.2.0. Для новых архивов и остальных private/runtime paths действует прежний запрет.

Исходный дефект воспроизводился на настоящем опубликованном ZIP: plan не находил blockers, но подтверждённый apply отклонял исторические шаблоны как private data. Checkout старого релиза и небольшой синтетический архив этого расхождения не показывали. Узкие тесты проверяют удаление, изменённые и отсутствующие preimages, сохранность неизвестных private-файлов рядом и запрет private payload в целевом архиве.

## Воспроизводимая проверка компонента

Workflow Public Core upgrade использует Windows и Linux runner с обычной Linux-файловой системой. Он собирает чистый candidate из точного checkout commit и загружает неизменяемые публичные assets:

- [ZIP](https://github.com/WebTolk/process-forge/releases/download/v1.2.0/processforge-1.2.0.zip): SHA256 0cd5c1f48ca0e94ddf5b0298b774a3498baf20e5a64b84dd9c05bbc0f36a2880.
- [Sidecar](https://github.com/WebTolk/process-forge/releases/download/v1.2.0/processforge-1.2.0.manifest.json): SHA256 2881c62ff279c9d418d7bb88ad01a321817c1c7454ec03e10227d3f6791d40bd.

Публичная 1.2.0 указывает source commit b70df739700f1559570f4b65481cd39616ccc1ea. До извлечения и запуска qualifier проверяет выбранные hashes, source commits, sidecars и каждый файл архивов. Commit/tree/hash кандидата, ОС, Python и результаты команд фиксируются в receipt; это не публикация стабильного релиза.

Workflow запускает tools/smoke_public_core_upgrade.py с явными public assets, candidate ZIP/sidecar, ожидаемыми commit/hash, новым собственным fixture root и приватным каталогом evidence. Публичная 1.2.0 однократно создаёт старые Workplace/проект и сохранённую Work, после чего выполняется внешнее обновление Core. Эта инициализация подготавливает старую тестовую установку и не является операцией обновления.

Проверяются read-only plan, подтверждение, локальные правки unchanged release files и отсутствие owned files, целевые bytes, настоящие preimages/absence, unknown files, побайтовая сохранность проекта/Workplace и прежние identity/checksum capsule сохранённой Work. Локальное runtime state не входит в release payload.

## Обязательная готовность проверяется отдельно

Успешная замена Core не создаёт native enrollment и не доказывает retirement старых writers. В воспроизведённом never-enrolled проекте публичной 1.2.0 последующие storage apply, context refresh, новая Work и worker prepare отказывают с storage_activity_unknown; execution inspect возвращает execution_activity_unknown. Этот file-only маршрут не предоставляет квалифицированный historical cold-to-managed deployment. См. [execution authority](../concepts/execution-storage.md) и [ST12](issue-17-storage-paths.md).

Receipt компонента записывает результаты миграции и worker prepare отдельно и явно оставляет full_t06_qualified=false. Зелёный job Core files не доказывает SQL cutover, native update или успешные worker start/status/collect. Configuration doctor и читаемость старой Work не доказывают готовность обычной записи. Missing/partial enrollment сохраняет native route и его отказы; file-only замена не является обходом.

| Требуемый результат | Оставшаяся граница квалификации |
| --- | --- |
| Миграция существующих хранилищ | Deployment authority, выбранные owner/routing/targets, исключение старых writers, identity, pending/resume и конечная SQL authority |
| Worker после обновления | Настоящие конечные prepare/start/status/collect после успешной обязательной миграции |
| Восстановление Core | Реальные failed/interrupted apply и поддерживаемые restore либо roll-forward; классификации repair недостаточно |
| Восстановление registry | Отдельный контракт package registry из issue18; это не Core или SQL rollback |
| Восстановление SQL | Проверенные snapshot/restore либо forward recovery после cutover с сохранением identity; универсальный downgrade поверх новых SQL commits не разрешён |

Issue19/Т06 остаётся открытой до прохождения всех исходных Windows/Linux, native/storage, worker, recovery и independent-review критериев. Существующая точная миграция Workplace к 1.1 не является общей цепочкой 1.2→candidate. Повторный workplace-init, fresh project initialization, legacy-write fallback и выдуманный retirement receipt не выполняют эти требования.
