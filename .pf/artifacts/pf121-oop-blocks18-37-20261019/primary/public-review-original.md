**Статус: changes_required.** Независимый source review двадцати блоков 18–37, всех шести вкладов и primary integration завершён. Открыто одно замечание средней серьёзности к сохранению тестовой fixture. Новых дефектов в перенесённых production-алгоритмах не обнаружено в пределах проведённого review.

Проверенный head: `ae111ca51f00676ea41d043285ef3cd9b19c0992`. Фиксированный baseline: `d0a50a5e51ec09fa97626756faf4a1c05e17afcf`. Состав двадцати коммитов взят из `primary/source-commits.json`; меняющийся HEAD для выбора версии не использовался. Обозначения `primary/` и `review2/` относятся к `.pf/artifacts/pf121-oop-blocks18-37-20261019/`.

Assignment: `p121-oop20-review2-20261019-independent-clean-context-source-review-of-t`; attempt 1. Run: `garage-p121-oop20-review2-20261019-independent-clean-context-source-revi`. Context: `p121-oop20-review2-20261019-independent-clean-context-source-review-of-t-capsule`.

**R002 — medium: фиксированные часы fixture заменены реальными.** Файл `tools/smoke_project_snapshot_read_composition.py`, строка 121, тест `test_start_preflight_uses_injection_before_capsule`.

На строке 115 локальный `core` задаёт `now_utc=lambda: 'now'`. В baseline `_start_locked` использовал именно этот callback. После переноса поле `_clock` на строке 121 получает `_core_common_clock.now_utc`; вызов `src/processforge_core/process_execution.py:325` теперь возвращает реальное время. Управляемая зависимость и прежние входные значения preflight потеряны. Текущие assertions часы не сравнивают, поэтому успешный прогон этого теста расхождение не опровергает. Падение теста или production-дефект этим замечанием не утверждаются.

`primary/consumer-integration-proof.json` прямо описывает требуемую вставку `object.__setattr__(service, '_clock', core.now_utc)` для сохранения fixture, но canonical-attribute replacement заменил локальный callback реальными часами. Это противоречит требованию brief сохранять fixture values и учитывать локальные bindings. LF SHA-256 проверенного теста: `bd11118c46d9210e4d788087cc5474867436d42fc397984a592c465e7dd3fee5`; ProcessExecutionService: `796957767825ce1c425d67fac6513dbc2f27243f25e949277174439aea3ab431`.

Требуемое исправление primary: передать тот же локальный callback, например `vars(core)['now_utc']`, и актуализировать только затронутые evidence/checksum. В первом тесте этого файла `core` не содержит `now_utc`: переносить туда такое обращение нельзя. Замечание передано собственным actor/session через native PF chat, сообщение `msg_345d1f226a62411391d3610f3b27f01d`. Reviewer продуктовые файлы не исправлял.

Проверены следующие вклады, их закреплённые reports, exports и proofs, а также фактические owning modules и относящиеся к ним изменения потребителей:

| Вклад | Блоки | Проверенная ответственность |
| --- | --- | --- |
| a | 18, 19, 20 | Setup answers, classifier sources, scan/inventory policy; явный distribution root, reuse registry inputs |
| b | 21, 24, 25, 37 | Release filtering/provenance, resource journals, public source policies; порядок ошибок и post-write dirty mark |
| c | 27, 28, 30 | Hook policy, chat export, telemetry и canonical clock; redaction, payloads, method binding |
| d2 | 31, 32, 34 | Rootless Run/task reader, consistency, orchestration config, observation inputs и общий process registry |
| e2 | 22, 23, 26 | Overrides, capability resolution, resource matching, buckets; rootless registry и snapshot inheritance |
| f | 29, 33, 35, 36 | Session metadata, supervisor inputs/state, agent registry, project coordination; frozen dataclass contracts |

Все 40 required-source byte pins текущей капсулы совпали. Все 88 закреплённых файлов совпали с Git blobs проверенного head и `primary/review-inputs/source-hashes.json`; checkout совпадает после нормализации CRLF→LF. В 16 файлах raw-хеш отличается только из-за окончаний строк. SHA-256 самого source manifest: `20549338af3153675eae79cee9c6d3d3f0df075ccbe48b0c3e0ff890e6aef5da`. Полная карта этих хешей включена в `review2/findings.json`.

Прочитаны Main/consumer integration proofs: 146 migrated bindings, удаление 127 прежних определений функций и 19 statements констант, 605 replacements глобальных обращений в Main и изменения 59 consumer-файлов. Сопоставлены owning imports, normal composition, YAML fallback, rootless inheritance, mutable registry identity, deferred dependencies и существенные изменения fixtures. Показатели proof используются как сохранённые свидетельства, а не как заново вычисленный reviewer паритет. В checksum inventory присутствуют все 23 новых Core-модуля; EN/RU ownership docs отражают фактические owners и оставшиеся границы миграции.

Поля `_clock` и `_event_paths` имеют `init=False`, `repr=False`, `compare=False`: добавление не меняет параметры конструктора, match arguments или сравнение/repr. Factories получают concrete Core callbacks без чтения часов и документов при создании; application services вызывают их отложенно. Relocation failure injection журнала корректно передаёт `self` сохранённому unbound method и восстанавливает class attribute в `finally`. Исключение из общего вывода о сохранении controlled fixtures — R002 выше.

После чтения результата повторно прочитаны все девять исходных архитектурных документов. Применён разрешённый `primary/python-knowledge.md`, SHA-256 `f01e8c9fad4d1a3419cb32531819030bb8331bae63519a02b2a88355261e9f1a`: явные owning imports, холодные конструкторы, descriptor binding, сохранение параметров и request-scoped reads. Чтение внешних Python manuals по этому digest не заявляется.

| Решения / инварианты | Сопоставление с фактическим результатом |
| --- | --- |
| D01/D02/D09 | Связные реализации принадлежат конкретным Core-модулям; выбранные callers используют owners. Возврата перенесённой реализации в Main через callbacks, providers или deferred imports не найдено. Неперенесённые обязанности не объявлены завершёнными. |
| D03/D04/D08/D10 | Применена конкретная композиция; новый Kernel, container, plugin loader, permission framework или REST отсутствует. Полная lifecycle/provider-архитектура этими блоками не реализована и не принимается. |
| D05/R06 | Rootless registry/Run/task/supervisor операции не требуют фиктивного distribution root. Frozen dataclass fields и constructor contracts сохранены. YAML остаётся live read через прежние readers/request scope; постоянный parsed-document cache не добавлен. |
| D06/R01/R04/R05/R08 | При переносе сохраняются существующие identity/access/provenance и transport guards. Required outputs, DI и ownership не превращены в grants. Полная security/admission квалификация не выполнялась. |
| D07/R02/R03/R07/R11 | Сохранённые proofs и чтение кода подтверждают прежние algorithms, unknown fields, native exceptions и порядок guards/reads/writes. Shared process registry единственный. Pinned stage selection, locks, evidence и recovery не переработаны. R002 требует исправления controlled clock в integration fixture. |
| D11/R09/R10/R12 | Review выполнен после реализации, отдельным artifact writer, с прямыми architecture pins и переносимыми ссылками. Историческое отклонение d2/e2 раскрыто ниже. Роли primary/reviewer и уровни source/delivery разделены; приёмка эпиков не заявлена. |

Историческое отклонение D11 остаётся фактом: narrowed d2/e2 scopes закрепляли brief/handoff, а не каждый архитектурный документ отдельно. Разрешённое чтение и записанные хеши подтверждают знакомство исполнителей с источниками, но не создают отсутствовавшие individual pins задним числом. Root/integration/current review имеют прямые pins. Содержание `primary/post-task-architecture.md` не трактуется как доказательство полного соблюдения прежнего admission; старые capsules не исправлялись.

Хеши перечитанных архитектурных источников; пути в таблице относительны `.pf/artifacts/`:

| Источник | SHA-256 |
| --- | --- |
| `oop-refactor-clarification-20261005/clarification.md` | `728b1fa837377cf8be32b549af8fd1d005ff9332f76409da45510d46f31ee01d` |
| `original-architecture-alignment-20261010/migration-contract.md` | `016a7485060bc39cdd448ccb38087954550f89f2b84e52959bdc52de6a9f15a4` |
| `pf-framework-architecture-20261005/adr.md` | `076acfe9c8df09f9408556d144840e60ac4a594b064bfe9ada3981e7e39cb550` |
| `pf-framework-architecture-20261005/domain.md` | `c90fe925601522e0f45fb13c282547d7f17e87d958d6c718d7345599557ab649` |
| `pf-framework-architecture-20261005/direction.md` | `23d68db7ffe463d1e63ea96acaff6104256c8e658d9baee9e4cfc9fa3445ba14` |
| `progressive-oop-boundary-20261010/decision.md` | `63c68bd61176d5cd3ab1e27791d3cc43657f2d750dac162b15e4da55e43e616b` |
| `python-framework-20261005/oop-02.md` | `c6462768f3aac61ca77c9268e7b32be00193719e5a9dda3896c99c231336d647` |
| `python-framework-20261005/oop-03.md` | `38d1fd36d54a9c4cf5de0c9fef212dafca034c98b27622ddd64e5c8fbc1f0522` |
| `python-framework-20261005/oop-05.md` | `26ceb97ab62124026378cb40815fc966cd883a20a6c7635a8595ad33e047f274` |

Граница доказательства — source. Прочитаны сохранённые результаты 15 focused checks primary, включая 61 unittest case, conditional skips и недоступные Windows symlink cases. Reviewer не повторял успешные tests/parity/compile, не добавлял suite и не выполнял archive/package-shaped/installed/live Runtime/connected MCP квалификацию. Native CLI chat/heartbeat не считаются такой квалификацией. Проверка выполнена разрешённым чтением файлов и фиксированного Git diff; внешние MCP/Serena resources без grants не использовались.

Предшествующее execution-contract R001 устранено successor: artifact-only write scope и собственная native coordination разрешены явно. Capsule SHA-256: `c5a29c0691e29c22f97b05d76a5ba40518dcf1b1c6254c47ae7ebdc714fd722d`. Actor/session совпали с launch environment; READ_ACK `msg_a1e27218796c4b8b8f70133e43d6a9d3` записан и прочитан обратно, heartbeat успешен. Новые Work, context rebuild, Git/index/remotes, lifecycle, peer/product writes и infrastructure actions reviewer не выполнял.

После публикации результата сохраняется текущая сессия с native heartbeat и опросом только собственного transcript для bounded follow-up/STOP до `2026-10-20T05:00:00Z`. Исправления, acceptance, Git, delivery и lifecycle принадлежат primary. `pass` для исходного head до разрешения R002 не выдан.
