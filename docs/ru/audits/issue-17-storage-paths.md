# Пути хранения: реализация и квалификация восстановления

Конечная инвентаризация сопровождает проверки для №17 / T05.
Приёмка должна указывать точную проверенную ревизию и квитанции выполнения на ОС.
Строка описывает границы реализации, а не квалифицированную установку или PASS.
Каждый путь требует указанных доказательств владения и безопасности. Тест с injected host proof
или UUID metadata не квалифицирует границу старых писателей в установке.
Обслуживание PF Core и lifecycle пакетов имеют разных владельцев:
обновление пакета не запрашивает обслуживание всего рабочего места.

Flow root проекта выбирается явно. Main profile по умолчанию — `project_main`
с путём `data/pf.sqlite3`; разрешённый alias обязан совпадать с существующим
execution binding. Identity проекта берётся из явного manifest `project.id`,
а не имени каталога.

| ID | Вход и реализованный переход | Authority и восстановление |
| --- | --- | --- |
| ST01 | `select_execution_storage`: подключение ready main по точным binding/profile. | Сохраняются project/store identity. Pending, отсутствующий, foreign или конфликтующий bound store дают отказ без JSON fallback. Чтение не создаёт store или identity; временные SQLite sidecars не являются доменными данными. |
| ST02 | `storage_identity_access`: подключение recognized ready events/raw/accounting/search store по owner slot. | Owner identity gate удерживается до закрытия adapter connection. Проверяются UUID, scope/owner, kind/path и доменная схема. Pending и unpinned adopted metadata запрещены. |
| ST03 | `migrate-storage.py --apply`, update/first-write coordinator: UUID adoption существующей recognized DB на месте. | Сохраняются доменные IDs, rows, blobs, объекты схемы и путь. Active/unknown до pending откладывают adoption без нового UUID и скана истории. Exact selector/plan/pending публикуются до mutation. |
| ST04 | `migrate-storage.py --resume`: восстановление точного adoption plan. | Используются прежние UUID, descriptor, source facts, backup и generation. Metadata commit с отставшим file journal восстанавливается вперёд. Targets коммитятся независимо; поздний отказ не откатывает ready target. |
| ST05 | `journal-maintenance execution-import`, coordinator main import: latest snapshots и allocation floors в main SQL. | Нужны qualified quiescence и exclusion старых писателей. Pending binding публикуется первым. Batch ≤256, import и checkpoint одной transaction. Единственный ready/sql CAS устанавливает authority. Утраченную историю не выдумывают. |
| ST06 | `execution-resume`, coordinator main recovery. | Exact migration/checksum/evidence selectors и прежние backup/checkpoint. До cutover перепроверяются frozen sources и safety. После ready SQL остаётся authority, JSON — только projection. |
| ST07 | `new_store_identity` плюс `add_store_identity`: явная инициализация нового writable domain target. | Pending предшествует созданию, metadata коммитится вместе с доменной инициализацией. После сбоя используется тот же UUID. Inventory не создаёт неиспользуемые absent stores. |
| ST08 | Explicit successful new-flow initialization: fresh main SQL and project journals. | Эксклюзивное создание и native capability закрепляются durable receipt; main/events готовы до обычных событий. Existing/forced root не считается новым; recovery сохраняет UUID и не даёт полномочий над workplace. |
| ST09 | Offline rename сохраняет подключение SQL по относительному пути; подготовленные попытки остаются привязаны к прежнему корню. | Engine fixture подставляет safety. Физический fixture нового проекта завершает worker, переименовывает весь каталог и проверяет main identity, файлы и принятый отчёт; повтор старой попытки запрещён. Это не успешный сквозной перенос всех stores/native bindings. |
| ST10 | `journal-maintenance backup/verify/restore`: один SQLite snapshot в verified bundle и новый absent destination. | Учитывается committed WAL, сохраняются UUID/data и bundle. Existing/unsafe/tampered destination запрещён. Restore не переключает live binding. Снимки нескольких DB независимы. |
| ST11 | `journal-maintenance inspect/import`, legacy `migrate-hook-journals.py`: recognized events/raw journals в project journal DB. | Сохраняются IDs/envelopes, originals, quarantine и backups. Writer cutover принадлежит оператору. Drift/conflicting duplicate запрещены даже с skip-invalid; после сбоя остаётся incomplete barrier для явного retry. |
| ST12 | Обновление архива Core: managed replacement, qualified Windows cold handoff либо отдельный file-only update. | У этих путей разные предусловия. Managed publication использует maintenance в свежем дочернем процессе; file-only update не даёт authority для миграции storage. Сохраняются exact selection/epoch и UUID/bindings там, где они применимы. Linux primitives не дают полного cold-to-managed перехода. |

## Recognized target layouts

Пути относительны выбранному flow root проекта либо workplace root.

| Scope / kind | Путь | Источник stable owner |
| --- | --- | --- |
| Project events | `runtime/events/events.sqlite3` | Явный project ID в manifest |
| Project raw | `runtime/agent-events/hooks.sqlite3` | Явный project ID в manifest |
| Standalone project search | `runtime/local-resource-search/search.sqlite` | Явный project ID; только без workplace |
| Project main | `data/pf.sqlite3` либо exact selected profile alias | Явный project ID; execution binding без второго legacy pin |
| Workplace raw | `runtime/agent-events/hooks.sqlite3` | Stable ID выбранного workplace manifest |
| Workplace search | `runtime/search/local-resource-search.sqlite` | Stable ID выбранного workplace manifest |
| Workplace accounting | `data/accounting/accounting.sqlite3` | Существующий origin ID из `data/accounting/identity.json` |

Отсутствующая workplace/accounting identity даёт per-target unqualified diagnostic.
Targets должны быть внутри выбранных owner roots и физически различны.
Изменение profile не переносит bound DB.

## Отсутствующие автоматические переходы

Не реализованы произвольный live rebind, restore поверх bound live DB,
old-Core rollback после SQL commits и adoption неизвестных remnants. Restore
создаёт новый destination; controlled offline binding switch выполняется отдельно.
Old-Core rollback требует отдельно qualified reverse export. Execution abort
ограничен границей до mutation; committed import/schema восстанавливается вперёд.
Новый workplace main, объединение всех legacy-доменов и другие drivers вне состава.


## Обязательная готовность и граница совместимости

Новые проекты должны начинать с актуальных SQL journals/stores. Старые проекты
должны завершить миграцию и проверить identity, schema и readiness до обычных
изменяющих операций Work или worker. Unknown/deferred блокирует запись;
чтение старого формата относится к явной миграции/восстановлению. Обычный legacy
fallback не является поддерживаемой политикой.

[ensure_execution_storage_ready][F] вызывает coordinator и затем повторно
выбирает SQL; одного отчёта об успехе недостаточно. [select_execution_storage][C]
может вернуть legacy route для некоторых unbound reads. Управляемый
[adapter_identity_access][AD] теперь передаёт намерение записи при выборе host,
отказывает при отсутствии владельца и blocked readiness даже с `legacy_allowed`
и требует проверенную identity хранилища до writable access. Ни `automatic=False`,
ни `migrating=True` журнала не предоставляют полномочий миграции. Самостоятельное
использование библиотеки вне управляемой операции остаётся отдельным случаем.
[Admission test][SA] `test_ordinary_large_legacy_write_refuses_before_any_history_scan`
проверяет отказ без сканирования истории и добавления записи. [UUID tests][ID]
охватывают четыре домена адаптеров и квалифицированное создание/adoption;
[configuration tests][CA] — явный и выбранный операцией host без потери write identity.

[Долгосрочное правило контрибьютера](../../../CONTRIBUTING.ru.md#готовность-хранилища-и-обязательная-миграция)
требует строгого SemVer с оценкой опубликованных контрактов глазами пользователя
и его агентов, без привязки политики к одному релизу. Небольшая поддерживаемая
миграция проекта сама по себе не требует MAJOR, если сохраняется совместимость
сценариев, публичных интерфейсов, интеграций и гарантий данных/идентичности.
Реальный слом публичного контракта требует MAJOR даже при наличии инструментов
миграции. Промежуточные нерелизные fallback и тесты не добавляют публичных контрактов.

Для действительно нового проекта [fresh_project.py][FP] фиксирует эксклюзивное
создание flow root с квалифицированной native capability и заранее сохраняет UUID
доменов. Main SQL и events готовы до первого события onboarding; project raw/search
создаются при первом использовании с теми же запланированными UUID. Восстановление
проверяет receipt, физический root, владельца и routing; готовое исчезнувшее или
чужое хранилище не пересоздаётся. Полномочия проекта не распространяются на workplace.
[Тесты fresh domains][FD] проверяют порядок первого события, прерывания,
сохранение UUID, отказы и разделение полномочий с подставленной capability;
реальный lifecycle отдельно проверяет [fresh-native-SQL][FN].

## Матрица критерий → исходный код / тест

Символы указаны относительно файла по ссылке. Это определения поддерживаемых
тестов, а не результаты их запуска в данном аудите. Safety в engine fixtures
синтетическая, даже если SQLite, файлы, WAL и subprocesses настоящие. Обязательные
физические доказательства остаются **pending**, пока результат не указывает точную
ревизию, OS/provider, выбранные случаи, исход и сохранённые recovery evidence.
Недоступный обязательный сценарий не становится N/A.

| Путь / критерий приёмки | Исходный код | Поддерживаемые тесты и границы доказательства |
| --- | --- | --- |
| ST01: точный attach; без fallback при недоступном bound main | [composition.py][C]: `select_execution_storage` | [test_compatibility.py][CP]: `test_pending_binding_missing_db_never_legacy_fallback`, `test_plan_and_binding_identity_tampering_refuses`; [test_configuration_access.py][CA]: `test_bound_storage_never_falls_back_to_projection`. [test_physical_storage_paths.py][PH]: `test_bound_physical_target_refuses_without_fallback` использует sealed CLI с отсутствующей, повреждённой, чужой БД, будущей версией формата, изменённым checksum схемы и directory alias; `test_real_wal_writer_contention_preserves_sql_authority` проверяет отказ при конкурирующей записи SQLite и последующее восстановление. |
| ST02: UUID адаптера и owner gate до закрытия connection | [storage_migration.py][S]: `storage_identity_access` | [test_storage_uuid.py][ID]: `test_pending_access_blocked_and_ready_access_holds_gate`, `test_adapter_ready_replacement_different_uuid_refuses`; [test_configuration_access.py][CA]: `test_adopted_legacy_access_uses_exact_pin_and_search_keeps_uuid`. Покрытие доменов не доказывает native eligibility. |
| ST03: recognized adoption на месте; точные rows/blobs/schema; отказ до UUID | [storage_migration.py][S]: `_target`, `_apply_target` | [test_storage_uuid.py][ID]: `test_known_formats_in_place_uuid_parity_and_replay`, `test_unknown_or_active_defers_without_uuid_or_maintenance`, `test_unknown_extra_objects_refuse_without_relabel`. Proof подставлен; exclusion писателей установки — pending. |
| ST04: прежние selector/UUID/backup, восстановление после commit до file journal | [storage_migration.py][S]: `resume`, `_load`, `_repair_ready` | [test_storage_uuid.py][ID]: `test_selector_before_pin_crash_never_remints`, `test_crash_after_commit_or_publication_recovers_exact_uuid`, `test_two_targets_progress_independently`. Fault injection не доказывает восстановление после физической смерти controller. |
| ST05: точные snapshot bytes/floors, ограниченные batches, атомарный checkpoint | [execution_migration.py][E]: `_batches`, `_import`, `_cutover` | [test_migration.py][M]: `test_success_exact_bytes_and_one_cutover`, `test_mixed_floor_batches_are_bounded_and_replay_exact`, `test_empty_record_batch_floor_and_checkpoint_rollback_together`. Есть случай 257 units; safety подставлена. |
| ST06: детерминированный resume; отказ при corrupt/drift evidence; authority остаётся SQL | [execution_migration.py][E]: `resume`, `_verify`, `_ready` | [test_migration.py][M]: `test_interruption_and_exact_resume`, `test_corrupt_backup_blocks_resume`; [test_compatibility.py][CP]: `test_committed_resume_does_not_reimport_updated_json`. Native interruption/cutover qualification — pending. |
| ST07: pending нового домена до создания; тот же UUID после сбоя | [storage_migration.py][S]: `new_store_identity`, `add_store_identity` | [test_storage_uuid.py][ID]: `test_explicit_new_initializer_pins_before_creation_and_commits_metadata`, `test_explicit_initializer_before_creation_retries_same_uuid`. `test_governed_journal_writes_after_qualified_creation_or_migration` проверяет готовую identity до записи с engine proof; native exclusion старых писателей остаётся отдельным требованием. |
| ST08: fresh main SQL; pending repair; отказ записи в старый проект | [composition.py][C]: `_initialize_fresh_execution_storage`, `_repair_fresh_execution_storage`; [first_write.py][F] | [test_automatic.py][A]: `test_fresh_initialization_uses_alias_and_repairs_same_pending_uuid`; [test_required_write_readiness.py][RW]: `test_actual_cli_refuses_unmigrated_project_without_private_paths`, `test_success_report_must_be_followed_by_ready_sql_selection`; [test_fresh_native_sql.py][FN]: `test_fresh_sql_worker_lifecycle_clears_resolved_unknown`. Наличие native backend — предусловие, не PASS. |
| ST09: offline-перенос без потери identity/ресурсов | [composition.py][C]: relative binding selection; [pf_native_control.py][N]: `ManagedEnrollmentProducer._binding` | [test_migration.py][M]: `test_project_move_preserves_relative_binding_and_identity` проверяет engine rename. [test_physical_storage_paths.py][PH]: `test_offline_move_preserves_sql_but_refuses_bound_attempt_reuse` проверяет физический rename, сохранность SQL/файлов/отчёта и отказ повторного использования старой попытки. Это не квалификация переноса всех stores или нового native lifecycle после переноса. |
| ST10: committed WAL snapshot; exclusive restore с сохранением UUID | [backup.py][B]: `SQLiteBackupService.create/verify/restore` | [test_backup.py][BT]: `SQLiteBackupTests.test_wal_commits_are_included_without_changing_source_bytes`, `test_existing_restore_destination_is_preserved`; [test_storage_uuid.py][ID]: `test_backup_restore_of_adopted_store_preserves_uuid`; [test_acceptance.py][IT]: `test_cli_backups_include_committed_wal_and_restore_exclusively`. Одна DB, без live rebind и общего атомарного snapshot нескольких stores. |
| ST11: сохранение journal IDs/envelopes/originals; conflict refusal и incomplete barrier | [journals.py][J]: `JournalMaintenanceService.migrate`, `_flush` | [test_journals.py][JT]: `test_conflicting_source_ids_refuse_before_mutation_even_with_skip`, `test_interrupted_import_keeps_both_barriers_and_retry_does_not_duplicate`, `test_batch_failure_rolls_back_only_current_batch_and_retry_preserves_prior_commit`; [test_acceptance.py][IT]: `test_cli_refusal_quarantine_explicit_skip_replay_and_legacy_entrypoint`. Writer cutover требует отдельного доказательства. |
| ST12: publication/recovery и storage readiness принимаются отдельно | [update.py][U]: `apply_update`; [pf_native_control.py][N]: `replace_core`, `_run_update_child`; [file_update.py][FU] | [test_native_control.py][NT]: `test_joint_real_updater_and_independent_successor_child`, `test_real_updater_retained_target_repair_force_and_authority`; [test_cold_handoff.py][CT]: `test_unqualified_default_refuses_even_synthetic_reset`, `test_g2_interruption_resume_and_corrupt_backup`; [test_file_update.py][FT]: `test_actual_external_sealed_cli_updates_manifest_only_target`, `test_complete_or_partial_managed_markers_never_fall_back`. Ограничения provider ниже; installed/source presence недостаточно. |
| Все пути: без внешнего file/process/network I/O внутри SQL transactions | [execution_migration.py][E]: готовые batches до `_import`; [storage_migration.py][S]: metadata writes отделены от backup/journals; [journals.py][J]: готовые bounded rows до `_flush` | [test_storage_admission.py][SA]: `test_migration_application_io_stays_outside_sql_transactions` проверяет выбранные Python I/O на шести маршрутах по настоящему состоянию SQLite transactions. Admission fixtures остаются synthetic; native retirement и произвольный extension I/O этим не подтверждаются. |

## Границы переноса и Core providers

ST09 не является общей командой relocation или протоколом произвольного rebind.
Относительные storage paths позволяют rename в engine fixture, но native
`ManagedEnrollmentProducer._binding` включает абсолютный root и физические
device/inode identities. Перенос проекта не доказывает валидность выбранной
installation/owner set. Этот тест не подтверждает полный перенос установки
или автоматическое исправление таких bindings. Физический fixture дополнительно
показывает, что [prepared input][PI] сохраняет абсолютный корень проекта и проверяет
его при загрузке. Повторный prepare собранной попытки после rename возвращает
`temporary_cleanup_blocked:ValueError`; неизменяемый input и принятый отчёт сохранены.
Готовая БД по новому пути не разрешает переписывать записи этой попытки.

У ST08 отдельное native-предусловие: [supports_owned_execution][N] проверяет
реальное удерживаемое владение деревом процессов на Windows или Linux. Portable
captured image может поддержать fresh SQL initialization при успешной проверке;
это не доказывает retirement писателей старой установки.

Проверенный source-вход сохраняет public inventory в памяти; обычный импорт
библиотеки остаётся cold. Приватные данные проекта в `.pf` исходной копии остаются
изменяемыми вне образа Core, с проверками alias/hardlink. Import и явные spec-loaders
по-прежнему отклоняют неопубликованный код. Граница приватных данных sealed-образа
не меняется. Стандартный temporary-file staging доступен приватным данным проекта;
пути опубликованного кода по-прежнему отклоняют custom openers. Тесты source
initialization проверяют внешний проект и проект внутри игнорируемой `.pf/tmp`.

`test_fresh_native_lazy_project_domains_keep_uuid` отдельно проверяет source
и sealed native-входы без подмены capability. После создания standalone-проекта
raw/search лениво создаются через обычные adapters, а второй процесс повторно
открывает stores. Сохраняются UUID из receipt, ready pins, дедупликация events/raw,
физическая identity search-файла и main binding.

`test_migration_application_io_stays_outside_sql_transactions` наблюдает настоящие
SQLite transactions при execution import, adoption всех четырёх признанных доменов
и journal import. Проверяются Python file open/scan/fsync, backup, process
creation/wait/signal и network calls; контрольная транзакция подтверждает отказ
монитора при файловой записи. Сканер завершает транзакцию своего временного индекса
дедупликации до передачи управления дальнейшему source/quarantine I/O или target
importer. Это ограниченное transaction-доказательство с fixture admission,
отдельное от native old-writer qualification и произвольного extension-level I/O.

У ST12 три разные границы реализации:

- Managed replacement требует существующего qualified enrollment. В
  [pf_native_control.py][N] `LegacyManagedBoundary.__init__` и
  `ManagedEnrollmentProducer.begin_managed_installation` отказывают вне Windows;
  `_legacy_closure` возвращает unknown. `replace_core` публикует под exclusive
  lease, затем `_run_update_child` независимо удерживает lease successor.
  Результат публикации файлов сам по себе не доказывает успешную storage migration.
- First cold adoption потребляет [pf_cold_controller.py][K] `Authority`, а не
  флаг вызывающего. `Windows` работает только на Windows;
  `Policy.qualified_versions` по умолчанию пуст, а `retirement` требует
  qualified observations точной сборки. Gate/boot seams в
  [test_cold_handoff.py][CT] не доказывают positive deployed retirement.
  [pf_linux_cold_controller.py][L] `ControlledCohort` и `FrozenTreeFence`
  реализуют более узкие primitives; они не подключены как `Authority`,
  потребляемая `from_cold_provider`. Полный Linux cold-to-managed route в этой
  ревизии не поддерживается. T05 не требует изобретать новый backend; обязательные
  Linux evidence для уже поддерживаемых путей остаются pending при недоступности.
- [file_update.py][FU] `file_update_candidate/apply_file_update` поддерживает
  отдельный sealed unbound installer и непересекающийся manifest-owned target,
  который никогда не был enrolled. Даже частичные managed markers запрещают
  fallback. Путь фиксирует archive bytes, сохраняет preimages и правдивый failure
  journal, использует mutex для cooperating updaters. Он не выполняет enrollment,
  retirement посторонних interpreters и не разрешает storage migration.
  `bootstrap_entry` может получить portable file-only image без control/epoch;
  это не native exclusion proof.

## Статус доказательств и условия завершения

[Storage recovery qualification][WF] задаёт Windows/Linux jobs, сохраняет JUnit
и запрещает skips выбранных случаев. В Linux явно исключены два Windows-only
device-name/junction cases; применимые symlink/reparse cases требуют настоящих
результатов. Выбраны migration/UUID/automatic/admission, database, backup, journal
и projection suites, а также physical storage paths, required-write-readiness
и fresh-native-SQL, fresh project domains и configuration access. В selection **нет**
native-update, cold-handoff и file-only
update suites.
[Linux native execution][LW] отдельно выбирает fresh-native-SQL и native lifecycle
tests и запускает controlled-cohort suite.

Описание workflow не является квитанцией выполнения. Физический набор проверяет
sealed fresh SQL, отказ для недопустимого bound target, реальную конкуренцию писателей
и существующую границу offline rename. Приёмка должна ссылаться на Windows/Linux
результаты проверенной ревизии с сохранением полезных отказов и исправленных запусков.
Этот инкремент не подтверждает полный перенос всех stores, qualified retirement
старых писателей/cold transition, физическое прерывание cutover или универсальную
инструментальную проверку transaction I/O. Обязательные доказательства для этих
реализованных путей остаются pending; низкоуровневые тесты с подставленным proof
их не заменяют. Новый неподдерживаемый relocation или Linux cold backend здесь
не добавляется.

См. [Execution storage and authority](../concepts/execution-storage.md),
[SQLite maintenance](../concepts/sqlite-journal-maintenance.md) и
[English inventory](../../audits/issue-17-storage-paths.md).

[C]: ../../../src/processforge_core/executions/composition.py
[F]: ../../../src/processforge_core/maintenance/first_write.py
[FP]: ../../../src/processforge_core/maintenance/fresh_project.py
[FD]: ../../../tests/execution_migration/test_fresh_project_domains.py
[S]: ../../../src/processforge_core/maintenance/storage_migration.py
[AD]: ../../../src/processforge_core/sqlite_storage.py
[E]: ../../../src/processforge_core/maintenance/execution_migration.py
[N]: ../../../tools/pf_native_control.py
[B]: ../../../src/processforge_core/maintenance/backup.py
[J]: ../../../src/processforge_core/maintenance/journals.py
[U]: ../../../src/processforge_core/maintenance/update.py
[FU]: ../../../src/processforge_core/maintenance/file_update.py
[K]: ../../../tools/pf_cold_controller.py
[L]: ../../../tools/pf_linux_cold_controller.py
[M]: ../../../tests/execution_migration/test_migration.py
[ID]: ../../../tests/execution_migration/test_storage_uuid.py
[A]: ../../../tests/execution_migration/test_automatic.py
[CP]: ../../../tests/execution_migration/test_compatibility.py
[SA]: ../../../tests/execution_migration/test_storage_admission.py
[CA]: ../../../tests/executions/test_configuration_access.py
[RW]: ../../../tests/execution_migration/test_required_write_readiness.py
[FN]: ../../../tests/execution_migration/test_fresh_native_sql.py
[PH]: ../../../tests/execution_migration/test_physical_storage_paths.py
[PI]: ../../../src/processforge_core/prepared/input.py
[NT]: ../../../tests/execution_migration/test_native_control.py
[CT]: ../../../tests/execution_migration/test_cold_handoff.py
[BT]: ../../../tests/maintenance_backup/test_backup.py
[IT]: ../../../tests/maintenance_integration/test_acceptance.py
[JT]: ../../../tests/maintenance_service/test_journals.py
[FT]: ../../../tests/maintenance/test_file_update.py
[WF]: ../../../.github/workflows/storage-recovery.yml
[LW]: ../../../.github/workflows/linux-native-execution.yml
