# Отчёт агента: release integrity и linked installation

- Assignment: `remediation-release-integrity-design-20260730`
- Run: `pre-release-remediation-20260730`
- Agent: `codex-remediation-release-integrity-architect`
- Session: `pre-release-remediation-20260730-release-integrity-architect`
- Lease: `lease-remediation-release-integrity-architect-20260730`
- Режим: read-only research; изменены только ADR и этот отчёт
- Статус: проектирование завершено, product/release writes не выполнялись

## Итог

Все пять findings подтверждены по текущему коду и артефактам. Подготовлен
единый implementable contract для:

- consumer-проверки SHA-256 всего ZIP и каждого физического entry;
- manifest v2 с source provenance, official-pack inventory и
  deterministic/source-date metadata;
- безопасной проверки ZIP до любой распаковки;
- последовательного fallback generated launcher после stale candidate;
- отделения чистого installation archive от project `.pf`;
- единого version/update/changelog policy.

Главный release blocker шире исходного tamper-примера: текущий
`command_release_archive_test` после проверки только списка имён вызывает
`ZipFile.extractall`. Поэтому path/special-entry/duplicate validation является
обязательной частью PF-AUD-014, а не отдельным улучшением.

## Метод и источники

Serena была вызвана первой: onboarding выполнен, проект активирован. Symbol
extraction для `tools/processforge.py` недоступен (`Active languages: []`).
После этого использованы Serena pattern search и точечный PowerShell/`rg`
fallback для тел функций, release metadata и ZIP inspection.

Прочитаны:

- `.pf/AGENTS.md`;
- `.pf/process-forge.yaml`;
- assignment;
- accepted schema-authority ADR;
- pre-release audit и remediation plan;
- completed release-surface report;
- релевантные символы `tools/processforge.py`;
- `tools/smoke_first_run.py`;
- checksum/schema/public validators;
- `VERSION`, `CHANGELOG.md`, update index/schema;
- `.processforge-releaseignore`;
- текущие `dist/processforge.zip` и manifest.

Execution Context Capsule не перестраивался: assignment запрещает worker
context rebuild. Работа велась по schema-valid assignment и выданной Agent
Ledger lease.

## Подтверждённые findings

### PF-AUD-014 — consumer ZIP integrity

Точные символы:

- `inspect_release_archive` (`tools/processforge.py:6167`);
- `archive_manifest_freshness_checks` (`:6209`);
- `command_release_archive_test` (`:6240`).

`inspect_release_archive` читает `namelist()`, отбрасывает directory names и
сравнивает sorted names с manifest. SHA-256 entries вычисляются только
`archive_manifest_freshness_checks`, который вызывается при optional `--root`.

Текущая consumer-only проверка реально вернула:

```text
PASS: manifest file list matches zip entries
PASS: manifest files: 777
SKIP: extracted archive release-test
RESULT: PASS
```

Текущий ZIP имеет SHA-256
`3c30613ab1f34be018f6aa16b8f0bbaa95e6249a4bd722a64e4c508559020d6d`,
но manifest не содержит archive SHA. Его keys:
`files, generated_at, name, version`.

Дополнительные нарушения контракта:

- `namelist()`/name-keyed reads не являются надёжным способом проверять
  duplicate physical entries;
- нет size и total-entry contract;
- malformed JSON/ZIP обрабатываются исключением вместо управляемого FAIL;
- unsafe names, normalized/casefold collisions, symlink/special entries не
  проверяются;
- `extractall` вызывается до доказательства безопасности entries.

### PF-AUD-016 — stale linked launcher

Точный producer: `project_runtime_launcher_files`
(`tools/processforge.py:2968`). В generated Python:

- `distribution_from_workplace` начинается на `:3036`;
- `distribution_root` на `:3053`;
- `main` на `:3072`.

`distribution_root` немедленно возвращает project override, затем workplace
path, затем env. Наличие `tools/processforge.py` проверяется только в `main`
после выбора. Поэтому invalid higher-precedence path завершает процесс и не
даёт valid fallback участвовать.

Текущий `tools/smoke_first_run.py:156-179` закрепляет ошибочное поведение:
после подмены override на missing path он ожидает FAIL. Этот участок должен
стать positive fallback regression.

### PF-AUD-018 — provenance

Точные символы:

- `command_release_pack` (`tools/processforge.py:6121`);
- constants `PROCESSFORGE_VERSION`,
  `PROCESSFORGE_SCHEMA_BUNDLE_VERSION`, `RELEASE_ARCHIVE_VERSION`
  (`:35-39`);
- `command_version` (`:6112`).

`command_release_pack` использует current filesystem mtimes через
`ZipFile.write`, записывает wall-clock `generated_at`, но не Git/source-date и
не финальный ZIP hash. Clean Git precondition отсутствует.

Во время исследования:

```text
HEAD: 2e8941b995644dcdc259d3a1618a4fafbf2b42f4
tree: 41000df97c34c057838732052295a697c2023f2f
dirty entries: 190
```

Эти данные в текущем manifest отсутствуют. Высокое число dirty entries
ожидаемо для активного multi-agent remediation и не является обвинением
конкретного slice; оно доказывает, что текущий archive не может быть
публичным release artifact без source freeze.

### PF-AUD-023 — distribution/self-project boundary

Точные поверхности:

- `RELEASE_PF_PUBLIC_FILES`/`RELEASE_REQUIRED_PATHS`
  (`tools/processforge.py:5182-5213`);
- `release_source_files` (`:5270`);
- `require_flow_root` (`:632`);
- `command_doctor_project` (`:17422`);
- checksum selector `public_file_entries`.

Текущий ZIP содержит:

```text
.pf/AGENTS.md
.pf/hooks.yaml
.pf/process-forge.yaml
```

Archive-root `AGENTS.md` byte-for-byte равен `.pf/AGENTS.md`. Manifest с
`workplace.reference: auto` и `project.type: processforge-development`
позволяет `command_doctor_project` трактовать extracted distribution как
self-contained dogfooding project, хотя assignments/contexts/logs/reviews/
handoffs исключены.

Принятое решение:

- authored source `packaging/distribution-AGENTS.md` маппится только в root
  `AGENTS.md`;
- source project `.pf` не поставляется;
- checksum selector использует тот же archive alias;
- extracted `doctor-project .` FAIL как non-project;
- внешний sibling workplace, внешний project и его launcher проходят.

Это не отменяет уже принятые documentation/checksum fixes: coverage algorithm,
root translations, `packs/`, self-exclusion и external-root docs сохраняются.

### PF-AUD-025 — release metadata

Текущие независимые источники:

- `VERSION`: `1.0.0`;
- `RELEASE_ARCHIVE_VERSION`: `1.0.0`;
- `.pf/process-forge.yaml process_forge.version`: `1.0.0`;
- update index `product.current_version`/`stable.latest`: `1.0.0`;
- changelog latest heading: `1.0.0 - 2026-07-20`;
- update URLs: `https://example.com/...`;
- dist manifest version: `1.0.0`.

`1.0.0` уже объявлен released, поэтому пересобрать под тем же номером иной ZIP
нельзя. Требуется новая version decision. Минимум — `1.0.1`; если official
bundled packs являются новой продуктовой возможностью, рекомендован `1.1.0`.
Окончательное решение остаётся release owner.

## Manifest v2 и consumer contract

ADR фиксирует закрытый manifest с:

- schema/name/version/schema-bundle/release-eligibility;
- source-date и derived timestamp;
- Git commit/tree/dirty;
- ZIP filename/size/SHA-256/entry count;
- sorted official packs с version и manifest SHA;
- sorted files с path/size/SHA.

Порядок consumer проверки:

1. JSON/schema;
2. whole ZIP size/hash;
3. physical `ZipInfo` safety;
4. duplicate/normalized/casefold checks;
5. count/name equality;
6. streaming size/hash каждого physical entry;
7. только затем extraction.

Pair integrity отделена от publisher authenticity. Одновременная подмена ZIP и
sidecar остаётся задачей внешней подписи/доверенного канала.

## Launcher policy

Порядок неизменен:

```text
valid project override
-> valid workplace registry
-> valid PROCESSFORGE_HOME
```

Ключевое слово — `valid`: root существует и содержит
`tools/processforge.py`. Stale/invalid candidate записывается в ordered
diagnostics и не останавливает поиск. Fallback не меняет local manifest или
registry. При полном FAIL выводятся все три источника и причины.

## Test matrix

| Smoke | Что доказывает |
|---|---|
| `smoke_release_archive_manifest_v2.py` | consumer-only byte/size/count/ZIP hash, malformed manifest |
| `smoke_release_archive_unsafe_entries.py` | absolute/drive/UNC/traversal, duplicate/casefold/NFC, symlink/special pre-extraction rejection |
| `smoke_release_reproducibility.py` | same commit/source-date => same ZIP; dirty public pack blocked |
| `smoke_linked_launcher_relocation.py` | override/workplace/env precedence, fallthrough, diagnostics, no mutation |
| `smoke_clean_distribution_boundary.py` | authored root AGENTS, no `.pf`, extracted non-project, external install/onboard PASS |
| `smoke_release_metadata_coherence.py` | VERSION/changelog/update/manifest/packs coherence, placeholder URL rejection |
| updated `smoke_first_run.py` | stale override recovers through workplace/env rather than expecting FAIL |

Каждый negative test обязан проверять nonzero result и отсутствие extraction/
configuration mutation, а не только текст ошибки.

## Implementation scope

Три последовательных sole-writer этапа:

1. **Integrity implementation** — `tools/processforge.py`, release manifest
   schema, packaging AGENTS, selector validators и focused smokes. Не трогает
   version, checksums, dist.
2. **Metadata** — после явного version decision меняет только `VERSION`,
   changelog, update index/migration и source project version.
3. **Finalization** — после source freeze обновляет checksum inventory, строит
   ZIP/manifest и запускает consumer/extracted gates.

Полный список ownership приведён в ADR. Параллельный writer для main CLI,
checksum selector или `dist/**` запрещён.

## Остаточные решения и риски

- Release owner должен утвердить target version и реальные update URLs.
- External signature/attestation не входит в этот slice; это явно остаётся
  residual authenticity risk.
- Reproducibility гарантируется в supported toolchain; выбранная ZIP
  compression/version должна быть закреплена тестом.
- Изменение checksum selector после уже принятого PF-AUD-015 slice нужно
  интегрировать поверх его `public_file_entries()` реализации, не откатывая
  полное покрытие.
- Текущий `dist/**` намеренно не пересобирался и остаётся непригодным как
  подтверждение закрытия findings.

## Созданные артефакты

- `.pf/adr/pre-release-remediation-release-integrity-design-20260730.md`;
- `.pf/artifacts/pre-release-remediation-agents/release-integrity-architect.md`.

Product code, schemas, validators, checksums, version/update metadata и
`dist/**` не изменялись.
