# Итоговый отчёт по предрелизной санации ProcessForge

- Дата отчёта: 2026-07-30
- Рабочая папка: `D:\Dev\process-forge`
- Run: `pre-release-remediation-20260730`
- Исходный аудит: `.pf/artifacts/pre-release-product-audit-20260730.md`
- План санации: `.pf/artifacts/pre-release-remediation-plan-20260730.md`
- Итоговый пакет: `dist/processforge.zip`
- Итоговый manifest: `dist/processforge.manifest.json`
- Итоговый статус: **clean release package built; full release validation PASS**

## 1. Короткий вывод

Пакет ProcessForge собран заново после контролируемого среза санации и
дополнительной стабилизации release validation.

Финальная проверенная последовательность прошла:

- schema validation — PASS;
- public cleanliness — PASS;
- checksum inventory — rewritten and checked, PASS;
- `release-check` — PASS;
- `release-pack` — PASS, 790 files;
- source `release-test --root . --public --trace-smokes` — PASS,
  564.49 seconds;
- full `release-archive-test --archive dist/processforge.zip --root .
  --extracted-test full --timeout-scale 1` — PASS;
- clean rebuild after `clean --release` — PASS, 790 files;
- final full `release-archive-test` on rebuilt ZIP — PASS, extracted
  `release-test --public` 532.02 seconds.

The earlier suspected hang in
`smoke_specialization_freshness_tracks_definition_change.py` was not
reproduced. The smoke passed directly, passed through `release-test --only`,
and passed inside the full source and extracted archive gates. The previous
timeout was caused by the way validation was launched and logged: live logs were
placed under `.pf/runtime`, while `release-test` starts with `clean --release`
and removes `.pf/runtime`. On Windows this produced a locked-file conflict when
the log file was open.

## 2. Собранный пакет

`release-pack` выполнен после обновления checksum surface.

Артефакты:

- ZIP: `dist/processforge.zip`
- Manifest: `dist/processforge.manifest.json`
- ZIP entries: 790
- ZIP size: 996954 bytes
- ZIP SHA-256:
  `A7A3412AFD1083C3BC5A09EA1200AF3D21AB1E2D41B6A6976C06E324D56F96EA`
- Manifest size: 126956 bytes
- Manifest SHA-256:
  `778E2CB2027A46C40F41A2509A670FD3B999083C47749A450FE1871C3E25C3FB`
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

Final extracted archive test запускал полный `release-test --public` внутри
распакованного архива. Время вложенного public gate: 532.02 seconds.

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

## 8. Release validation stabilization

### 8.1. Full public release-test

Команда:

```powershell
python bin/pf.py release-test --root . --public --trace-smokes
```

Результат:

- PASS;
- elapsed: 564.49 seconds;
- trace: `.pf/runtime/release-test/latest-trace.ndjson`;
- `smoke_specialization_freshness_tracks_definition_change.py` прошёл в составе
  полного public gate.

Статус: **PASS**.

### 8.2. Full extracted archive test

Команда:

```powershell
python bin/pf.py release-archive-test --archive dist/processforge.zip --root . --extracted-test full --timeout-scale 1
```

Результат:

- PASS on pre-rebuild package;
- clean rebuild completed after `clean --release`;
- PASS again on final rebuilt package;
- final extracted public release-test elapsed: 532.02 seconds.

Статус: **PASS**.

### 8.3. Root cause of previous timeout

Previous external monitoring stored live release-test logs in `.pf/runtime`.
That path is intentionally removed by the first release-test step
`clean --release`. On Windows, deleting `.pf/runtime` while stdout/stderr log
files were open caused `PermissionError: [WinError 32]`. The validation itself
was stable after logs were moved outside the checkout to `%TEMP%`.

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

1. Добавить постоянный crash-recovery smoke для interrupted transaction /
   corrupted backup или явно оформить waiver.
2. Принять решение по release manifest contract:
   - текущий package manifest валиден для текущего tooling и quick archive
     validation/full archive validation;
   - release-integrity design требует более богатой provenance-модели, но
     после решения о first public `schema_version: 1` её надо проектировать как
     manifest v1 for release 1.0.0, а не v2.
3. Разобрать strict-contract backlog без broad rewrite:
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

1. Добавить постоянный crash-recovery smoke для interrupted transaction /
   corrupted backup или оформить явный waiver.
2. Принять release-manifest v1-for-1.0.0 provenance contract.
3. После этого повторить финальный release shield:
   - checksum `--write`;
   - checksum `--check`;
   - source `release-test --public`;
   - `release-pack`;
   - full `release-archive-test`;
   - `git diff --check`.
