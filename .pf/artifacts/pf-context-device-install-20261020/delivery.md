# Установка принятого исправления на устройство

## delivery-report
Прямое поручение оператора выполнено одним native apply --confirm.
Update: core-update-20261020T124659Z; status applied, exit0.
Source: 526c5d13e42e96693802760cce35fe896e208708, version 1.2.0 dev.
Archive SHA acaa0ff8b3b8a368520a7a115e3db14efe45c74555425f74ea116d9dd9b36457.
Применён именно ранее собранный пакет: 5 changed, 1453 unchanged, 0 added/removed,
0 local modifications. Force не использовался. Native migration not_applicable.
Никакой новый пакет или alpha release не создавался.

## installed acceptance
На установленном Core проверены все 1458 manifest-owned файлов: size и raw SHA
совпадают с новым manifest, source.commit совпадает с принятым source SHA.
Проверены пять backup preimages побайтно и старый manifest по полному JSON значению.
Native updater хранит control/old-manifest.json сериализованным: формат байтов
отличается от прежнего installed manifest, значения всех полей и file hashes равны.
Резервная копия находится в установленном Core runtime/core-update/backups/
core-update-20261020T124659Z; новая установка не повторяет утренний успешный update.

Сохранены 7 protected files, 243 Workplace YAML, 69 unowned static Core files
и 8 чужих source guards. Полный volatile Runtime/cache state не объявляется
замороженным; фильтры и private baseline сохранены для воспроизведения.
Installed module roots подтверждены под настроенным installed Core/src.
Native post-update doctor-workplace PASS: 197 PASS строк. Новый status installed,
incomplete_update=false; read-only repair: nothing_to_repair.

Installed CLI и source CLI согласованы: fresh context, fresh resources,
ready execution, continue policy, stale_resources [] на том же
ctx-20261020-072238-da5df2 и прежнем SHA
bd7dc7f033fe9f95f4c6903ea168868251db7666ef536c12479f7bcae667a05a.
Snapshot refresh и service restart не выполнялись.

## release-readiness-decided
Device installation READY/COMPLETE. Actual connected-host acceptance остаётся
PENDING пользовательского restart: текущий pf.context после apply всё ещё stale.
Это не повод повторять apply либо refresh. После restart наблюдать настоящий
подключённый MCP, его provenance и свежую пару CLI/MCP на равных inputs.
Не заменять это независимым stdio или новым несвязанным PID.

Будущая 1.3.0-alpha1 остаётся NO-GO по ранее записанным двум source препятствиям:
prerelease ordering и missing Path import в release smoke. Установка только
исправления контекста не меняет тот вывод и не объявляет альфу опубликованной.

## delivery-profile-run-or-skipped-with-reason
Native delivery profile выполнен по явному разрешению оператора, без restart
Runtime/MCP/host hooks/Ledger. Content audit ZIP и archive-test не выполнялись
согласно указанию пользователя; штатная валидация установщика сохранена.
Единый источник actual install evidence: apply.json, installed-verification.json
и context-parity-after-install.json. Raw native stdout/journal/baselines сохраняются
в собственной .pf/tmp/pf-context-device-install-20261020.
Handoff будет записан для новой сессии; текущая Work закрывает установку, без
утверждения actual-host proof и без повторного запуска прежней terminal source Work.
