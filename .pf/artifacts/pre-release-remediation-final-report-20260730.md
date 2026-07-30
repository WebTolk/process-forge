# Итоговый отчёт по предрелизной санации ProcessForge

- Дата отчёта: 2026-07-30
- Рабочая папка: `D:\Dev\process-forge`
- Run: `pre-release-remediation-20260730`
- Исходный аудит: `.pf/artifacts/pre-release-product-audit-20260730.md`
- План санации: `.pf/artifacts/pre-release-remediation-plan-20260730.md`
- Итоговый пакет: `dist/processforge.zip`
- Итоговый manifest: `dist/processforge.manifest.json`
- Итоговый статус: **package built; release candidate requires conditions**

## 1. Короткий вывод

Пакет ProcessForge собран заново после контролируемого среза санации.

Сборка и быстрые публичные gates прошли:

- schema validation — PASS;
- public cleanliness — PASS;
- checksum inventory — rewritten and checked, PASS;
- `release-check` — PASS;
- `release-pack` — PASS, 790 files;
- `release-archive-test --extracted-test quick` — PASS, manifest/ZIP/source
  hashes согласованы.

Полный public release gate **не засчитан как PASS**: команда
`python bin/pf.py release-test --root . --public --no-clean --trace-smokes`
не завершилась за 424 секунды и была остановлена вместе с её дочерними
процессами. Это не доказанный functional FAIL, но это release-blocker уровня
validation reliability: релиз 1.0.0 нельзя объявлять полностью проверенным,
пока полный gate не завершится или пока команда не будет разбита на
диагностируемые сегменты.

## 2. Собранный пакет

`release-pack` выполнен после обновления checksum surface.

Артефакты:

- ZIP: `dist/processforge.zip`
- Manifest: `dist/processforge.manifest.json`
- ZIP entries: 790
- ZIP size: 996954 bytes
- ZIP SHA-256:
  `FBE1274468B7E4EB8381E0F80C05E0D9E2F7322C5904B898103EA6D8736141F5`
- Manifest size: 126956 bytes
- Manifest SHA-256:
  `A903675AC2F17BFC89978427A86D0A2A90609DF05BF6E9A943BAC47EEDAC901D`
- Manifest version: `1.0.0`
- Manifest file count: 790

Archive validation:

```text
PASS: archive exists
PASS: manifest exists
PASS: archive forbidden entries: 0
PASS: manifest file list matches zip entries
PASS: manifest files: 790
PASS: archive entries match current root release file set: 790
PASS: archive file hashes match current root
PASS: manifest hashes match current root release file set
PASS release-test extracted archive
RESULT: PASS
```

Extracted archive quick test запускал только:

- `py_compile`;
- `schema validation`;
- `public cleanliness`;
- `checksum`.

Полный extracted archive test не запускался после source timeout, потому что он
ожидаемо повторяет тот же длинный public `release-test` внутри распакованного
архива и без предварительной стабилизации диагностики даст мало нового сигнала.

## 3. Что было обнаружено исходным аудитом

Исходный аудит обозначил релиз как **NO-GO**. Главные классы проблем:

1. мастера и registry-команды могли принимать небезопасные id/path формы;
2. aggregate gates местами давали ложный зелёный результат;
3. генераторы создавали сущности, не совпадающие с опубликованными schemas;
4. doctors принимали то, что должны были блокировать;
5. process lifecycle допускал несуществующие или конфликтующие процессы;
6. authoring операции могли оставлять частично созданные сущности активными;
7. release/archive integrity доказывал не всё, что должен доказывать для
   потребителя;
8. проектная `.pf` и installed/workplace слои смешивались в анализе сильнее,
   чем должно быть в публичном пакете.

## 4. Организация санации

Работа была оформлена как `.pf` run `pre-release-remediation-20260730` с
assignment/review/report артефактами.

Фактические группы задач:

- contract/schema authority;
- critical CLI boundaries and aggregate gates;
- schema/generator/doctor alignment;
- reusable-template contract correction;
- release surface / checksum surface;
- platform fixture alignment;
- knowledge builder contract;
- lifecycle/process design;
- provider/runtime design;
- release integrity design;
- transactional authoring implementation;
- transaction review and controlled finish;
- strict-contract audit and later сужение scope после решения по 1.0.0.

На поздней стадии пользователь уточнил существенное продуктовое решение:

- публичного релиза ещё не было;
- обратную совместимость не храним;
- релиз будет `1.0.0`;
- поэтому новые публичные contracts не должны начинаться с `schema_version: 2`
  только потому, что во внутренних черновиках была предрелизная форма.

Это решение отменило часть ранних рекомендаций агентов про reusable-template
v2 / release-manifest v2 как обязательный direction для 1.0.0. Текущий
контролируемый срез закрепил first public reusable-template contract как
`schema_version: 1`.

## 5. Принятые решения

### 5.1. Без legacy compatibility

Так как публичного релиза не было, нет обязанности тащить публичную обратную
совместимость. Но это не означает хаотичный rewrite: предрелизные формы должны
либо быть удалены, либо явно признаны внутренними историческими артефактами.

### 5.2. Release `1.0.0`, contracts v1

Для впервые публикуемых contracts в релизе `1.0.0` выбран
`schema_version: 1`. Это применено к reusable-template schema/template и
отражено в ADR:

- `.pf/adr/pre-release-remediation-no-compatibility-20260730.md`;
- `.pf/adr/pre-release-remediation-schema-authority-20260730.md`;
- `.pf/adr/pre-release-remediation-release-integrity-design-20260730.md`.

### 5.3. Узкий controlled finish вместо broad rewrite

После остановки агентов работа была сужена до:

- platform/knowledge/process transaction semantics;
- rollback/recovery verification;
- durable post-commit replay;
- dry-run/apply preflight parity;
- reusable-template first-public schema version.

Provider/runtime, lifecycle и release integrity designs сохранены как
следующие slices, но не реализовывались в controlled finish.

### 5.4. `.pf` как dogfooding, не публичная история продукта

Старая формулировка `v2` осталась в некоторых ранних отчётах агентов под
`.pf/artifacts/pre-release-remediation-agents/`. Эти файлы являются историей
процесса санации, а не public/runtime contract.

## 6. Что исправлено в коде и публичных контрактах

### 6.1. Transactional authoring core

В `tools/processforge.py` реализован общий transaction layer для authoring
операций:

- staged writes;
- preimage backups;
- journal state machine;
- rollback verification;
- explicit recovery command;
- persisted post-commit effects.

Ключевое поведение:

- `rolled_back` ставится только после проверки hash pre-existing файлов и
  отсутствия pre-missing paths;
- повреждённый backup переводит transaction в `recovery_required`;
- созданные директории удаляются только если они пусты и точно созданы этой
  transaction;
- `committed`, `committed_audit_pending` и `recovery_required` блокируют новые
  strict authoring mutations через incomplete journal detection;
- `authoring-transaction-recover` умеет dry-run/apply recovery/replay.

### 6.2. Post-commit replay

Post-commit effects теперь записываются в journal как serializable records:

- `process_event`;
- `knowledge_audit`;
- `platform_audit`;
- non-executable conditional hook placeholders.

Это убрало зависимость recovery от Python callback, который невозможно
восстановить после аварийного завершения процесса.

### 6.3. Platform staged semantic validation

`platform-create`/platform authoring validation проверяет staged platform
contract до публикации entity/registry writes. Это закрывает дефект, где
сломанный child contract мог попасть в registry до semantic FAIL.

### 6.4. Dry-run/apply parity

Dry-run для authoring paths теперь проходит общий `preflight_authoring_plan`.
Это снижает риск, что dry-run показывает безопасный план, а apply падает на
базовом контракте.

### 6.5. Reusable template first-public contract

`schemas/reusable-template.schema.json` и
`templates/reusable-template-template.yaml` приведены к единому first-public
contract:

- `schema_version: 1`;
- `type: reusable_template`;
- required identity fields;
- `files` обязателен как поле, но допускает пустой список.

Предрелизный split legacy/workplaceV2 из public schema убран.

## 7. Проверки, которые прошли

В ходе controlled finish и финальной сборки проходили:

- `python tools/smoke_remediation_transactional_authoring.py`;
- `python tools/smoke_remediation_platform_layout_strict.py`;
- `python tools/smoke_remediation_process_create_transaction.py`;
- `python tools/smoke_remediation_schema_inventory.py`;
- `python tools/smoke_remediation_generator_schema_alignment.py`;
- `python tools/smoke_remediation_aggregate_gates.py`;
- `python tools/smoke_remediation_security_boundaries.py`;
- `python tools/smoke_remediation_doctor_contracts.py`;
- `python tools/validate-process-forge-schemas.py`;
- `python tools/validate-public-cleanliness.py`;
- `python tools/validate-process-forge-checksums.py --root . --write`;
- `python tools/validate-process-forge-checksums.py --root . --check`;
- `python bin/pf.py release-check --root .`;
- `python bin/pf.py release-pack --root . --output dist/processforge.zip`;
- `python bin/pf.py release-archive-test --archive dist/processforge.zip --root . --extracted-test quick --timeout-scale 2`;
- `python -m py_compile tools/processforge.py`;
- `python bin/pf.py authoring-transaction-recover --help`;
- `git diff --check`.

`git diff --check` возвращал exit code 0; выводил только LF/CRLF normalization
warnings для уже изменённых файлов.

Дополнительные review probes:

- corrupted backup recovery returned `recovery_required`;
- created-directory rollback returned `rolled_back`;
- active docs/schemas/templates/tools/ADRs не содержат нового
  reusable-template v2/workplaceV2 public contract.

## 8. Проверки, которые не являются PASS

### 8.1. Full public release-test

Команда:

```powershell
python bin/pf.py release-test --root . --public --no-clean --trace-smokes
```

Результат:

- timeout after 424 seconds;
- stdout не был получен до timeout;
- обнаруженные дочерние процессы release-test были остановлены вручную;
- зависание было в районе
  `smoke_specialization_freshness_tracks_definition_change.py` /
  `project-context-refresh` по process command line.

Статус: **не PASS**.

### 8.2. Full extracted archive test

Не запускался после source timeout. Quick archive validation PASS, но full
archive validation остаётся обязательным gate перед публикацией.

## 9. Состояние assignment/review matrix

Assignments, завершённые успешно:

- `remediation-contract-architect-20260730`;
- `remediation-critical-cli-20260730`;
- `remediation-generator-doctor-cli-20260730`;
- `remediation-template-schema-correction-20260730`;
- `remediation-release-surface-20260730`;
- `remediation-platform-fixture-alignment-20260730`;
- `remediation-knowledge-builder-contract-20260730`;
- `remediation-lifecycle-design-20260730`;
- `remediation-provider-runtime-design-20260730`;
- `remediation-release-integrity-design-20260730`;
- `remediation-transaction-design-20260730`;
- `remediation-transactional-authoring-20260730`;
- `remediation-first-phases-final-review-20260730`;
- `remediation-controlled-finish-20260730`.

Assignments/reviews, завершённые как failed gate или obsolete-by-decision input:

- `remediation-first-slice-review-20260730` — failed review, затем исправления
  продолжены;
- `remediation-integrated-review-20260730` — failed integrated review, затем
  часть findings закрыта;
- `remediation-transaction-review-20260730` — failed transaction review,
  породил controlled finish;
- `remediation-strict-contract-audit-20260730` — failed strict audit, но его
  v2-направление частично superseded решением про first public `schema_version:
  1`.

Parent assignment:

- `pre-release-remediation-implementation-20260730` остаётся `in_progress`,
  потому что весь remediation backlog не закрыт как full release-ready.

## 10. Остаточные риски и условия перед публикацией 1.0.0

Release-blocking before publish:

1. Стабилизировать полный `release-test --public`, минимум диагностировать и
   закрыть hang around specialization freshness / project-context-refresh.
2. Прогнать full source public release-test до PASS.
3. Прогнать full extracted archive test до PASS.
4. Добавить постоянный crash-recovery smoke для interrupted transaction /
   corrupted backup или явно оформить waiver.
5. Принять решение по release manifest contract:
   - текущий package manifest валиден для текущего tooling и quick archive
     validation;
   - release-integrity design требует более богатой provenance-модели, но
     после решения о first public `schema_version: 1` её надо проектировать как
     manifest v1 for release 1.0.0, а не v2.
6. Разобрать strict-contract backlog без broad rewrite:
   - MCP auth model;
   - legacy/flat aliases;
   - provider/runtime contract;
   - lifecycle/process invariant enforcement;
   - package/workplace installed-tool boundary.

Non-blocking but important:

- сократить количество historical contradictory reports в handoff narrative;
- добавить явный release checklist item: historical `.pf` reports may contain
  superseded directions and must not be treated as current contract authority.

## 11. Текущее рабочее дерево

Рабочее дерево остаётся dirty. На момент финальной сборки `git status --short`
показывал 168 изменённых/untracked строк, включая:

- `.pf` artifacts/logs/assignments/reviews/run state;
- `tools/processforge.py`;
- remediation smoke tests;
- schemas/templates/docs/examples/packs from this and previous pre-release
  work;
- `checksums/processforge.sha256`;
- `dist/processforge.zip`;
- `dist/processforge.manifest.json`.

Это означает: пакет собран из текущего dirty source state. Для публикации нужен
отдельный clean-source release step: review diff, commit, повторить full gates,
собрать ZIP из принятого source state.

## 12. Handoff

Готовые артефакты:

- `dist/processforge.zip`;
- `dist/processforge.manifest.json`;
- `.pf/artifacts/pre-release-remediation-final-report-20260730.md`;
- `.pf/reviews/pre-release-remediation-controlled-finish-review-20260730.md`;
- `.pf/artifacts/pre-release-remediation-agents/controlled-finish.md`.

Рекомендуемый следующий узкий шаг:

1. Изолировать зависающий smoke:
   `smoke_specialization_freshness_tracks_definition_change.py`.
2. Исправить или ограничить timeout/reporting так, чтобы public release-test
   завершался детерминированно.
3. Повторить:
   - checksum `--write`;
   - checksum `--check`;
   - source `release-test --public`;
   - `release-pack`;
   - full `release-archive-test`;
   - `git diff --check`.
