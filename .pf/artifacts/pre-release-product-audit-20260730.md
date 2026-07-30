# Предрелизный аудит ProcessForge как продукта

- Дата: 2026-07-30
- Объект: текущий локальный release candidate `D:\Dev\process-forge`
- Ветка и commit: `main`, `2e8941b995644dcdc259d3a1618a4fafbf2b42f4`
- Сравнение: source checkout, `dist/processforge.zip`, чистая распаковка, сгенерированные workplace/project и рабочая проектная `.pf`
- Режим: read-only для кода и публичных файлов
- Итог: **NO-GO**

## 1. Резюме

Релиз блокируют не косметические расхождения, а нарушения базовых продуктовых
гарантий:

1. два мастера позволяют записать файлы за пределами выбранного resource root;
2. два агрегирующих release/authoring gate дают ложный зелёный результат;
3. мастера создают сущности, не соответствующие опубликованным JSON Schema, а
   собственные doctor-команды подтверждают их как исправные;
4. одна и та же версия процесса без предупреждения перезаписывается;
5. несуществующие процессы проходят через context resolver и creators;
6. ошибочно созданные или частично записанные сущности остаются активными;
7. проверка целостности архива не доказывает соответствие ZIP опубликованным
   SHA-256 в consumer-mode;
8. project-local launcher не выполняет заявленный контракт независимой замены
   linked distribution.

Штатный полный тест распакованного архива прошёл за 510,49 секунды, а source,
ZIP и manifest совпали по 777 файлам. Этот PASS не опровергает findings: сами
гейты не покрывают ряд проверенных нарушений и местами возвращают неверный exit
code.

Рекомендуется не публиковать текущий архив до исправления всех Critical и
минимум High findings PF-AUD-005—PF-AUD-017, добавления отрицательных
регрессионных тестов и повторной сборки из чистого, однозначно идентифицируемого
Git state.

## 2. Исходное состояние

До начала аудита рабочее дерево уже содержало незакоммиченный срез official
bundled process packs:

- 69 tracked paths изменены или удалены;
- присутствуют untracked `packs/`, schema, docs, smokes и проектные `.pf`
  артефакты предыдущего завершённого run;
- `HEAD == origin/main == 2e8941b995644dcdc259d3a1618a4fafbf2b42f4`;
- `dist/processforge.zip` и manifest соответствуют именно этому dirty state.

Аудит не изменял продуктовый код, schemas, docs, release ZIP или manifest.
Созданы только этот отчёт и служебные assignment/run/log/review/handoff в `.pf`.
Все разрушающие репро выполнялись в `%TEMP%` на копии распакованного ZIP.

Serena была вызвана первой, но у активированного проекта отсутствует
настроенный language backend (`Active languages: []`). После этого применялся
точечный shell fallback.

## 3. Блокирующие findings

### PF-AUD-001 — Critical — выход из package root через `knowledge-package-create`

`tools/processforge.py:19714-19720` принимает `args.id` как строку и строит
`package_root.resolved_path / package_id` без проверки canonical id и
containment. Те же raw-id helpers используются при разрешении пакетов
(`6830-6839`, `7417-7457`) и в hub build/release.

Репро:

```powershell
python bin/pf.py knowledge-package-create `
  --workplace <W> `
  --id '..\..\escaped-package' `
  --title 'Escaped Package' `
  --package-root global `
  --kind documentation `
  --apply
```

Факт: exit `0`, doctor — все `PASS`; `package.yaml` записан вне package root, а
CLI сообщает `packages/../../escaped-package/package.yaml`. С `--force` это
даёт возможность перезаписи доступного файла за границей выбранного root.

Ожидание: до proposal и любой записи валидировать id по единому контракту и
проверять, что resolved target находится внутри resolved package root.

### PF-AUD-002 — Critical — выход из specialization root

`specialization_resource_id` (`tools/processforge.py:3497-3498`) только добавляет
prefix. Create и path resolver (`3535-3563`, `20493-20523`) не проверяют
containment; doctor (`20450-20485`) не проверяет ни schema, ни безопасный путь.

Репро:

```powershell
python bin/pf.py specialization-create `
  --workplace <W> `
  --id '..\..\escaped-specialization' `
  --title 'Escaped Specialization' `
  --apply
```

Факт: exit `0`, doctor — все `PASS`; файл создан вне specialization root,
registry содержит `specializations/../../escaped-specialization.yaml`.

### PF-AUD-003 — Critical — `authoring-parity-check-all` возвращает 0 при FAIL

Resource failures учитываются в summary (`tools/processforge.py:13727-13752`),
но функция возвращает только `process_result` (`13755`).

Репро: в temp template внесён private/secret path. Индивидуальный
`template-parity-check` вернул 1; агрегатор записал:

```text
result: FAIL
resource_counts.FAIL: 1
```

но завершился exit `0`.

Влияние: прямой false green для CI и предрелизной проверки authoring masters.

### PF-AUD-004 — Critical — `release-test --only public-gate` не запускает public commands

CLI объявляет synthetic label `public-gate` (`tools/processforge.py:5885-5893`),
затем фильтрует команды по буквальному label, которого среди команд нет
(`5898-5899`). Остаются только `public_release_checks` (`5479-5507`):
отсутствие stale dist, помеченных parity WARN и mojibake.

Репро на чистой распаковке:

```powershell
python bin/pf.py release-test --root . --only public-gate --no-clean
```

Факт: exit `0` за 0,06 с, `RESULT: PASS with warnings`; schema, cleanliness,
checksums, release-check, smokes и doctors не запускались.

## 4. High findings

### PF-AUD-005 — схемы, генераторы и doctors описывают разные сущности

Подтверждены четыре семейства рассогласований:

- `knowledge-package-create` допускает dotted ids и `kind` =
  `rules|source|mixed`, но `schemas/package-manifest.schema.json:12,26` этого не
  допускает;
- все 8 проверенных manifest из
  `packs/official/*/knowledge-packages/*.yaml` и
  `seeds/knowledge-packages/*.yaml` не проходят package schema из-за dotted id;
- `template-create` генерирует manifest без `type`; он не соответствует ни
  `template-package.schema.json`, ни `reusable-template.schema.json`. Для
  `audit.template` встроенный validator сообщил соответственно 1 и 3 ошибки;
- `platform-create` и `platform-contract-install` записывают registry entry без
  обязательного `name` из `platform-registry.schema.json:18-21`;
- hub build пишет `kind: knowledge_package`, которого нет в package schema.

При этом package/template/platform doctors возвращают `PASS`. Public schema
validator проверяет root `packages/*.yaml` и official process/classifier files,
но не проверяет `packs/official/*/knowledge-packages/*.yaml` и
`seeds/knowledge-packages/*.yaml`
(`tools/validate-process-forge-schemas.py:816-864`).

Перед исправлением нужно выбрать один authoritative manifest contract, затем
синхронно обновить schemas, generators, doctors, examples/seeds и release
coverage.

### PF-AUD-006 — doctor-команды дают ложный PASS и могут скрывать потерю данных

Подтверждено:

- invalid YAML `package.yaml` заменяется синтетическим manifest в памяти
  (`tools/processforge.py:7457-7467`), после чего
  `knowledge-package-doctor` сообщает `manifest loaded`;
- invalid `registries/tools.yaml` не замечается `doctor-workplace`;
  последующий `tool-register` сбрасывает registry в пустой документ и
  записывает только новую запись (`20320-20330`);
- удаление `registries/process-packs.yaml` не замечается `doctor-workplace`,
  но все official packs становятся неактивными;
- `doctor-project` возвращает 0 после удаления schema-required
  `project.name` и установки `schema_version: 999`;
- `process-doctor --contract-only` принимает `status: bogus` и запрещённый
  unknown top-level key;
- `specialization-doctor` принимает manifest без required `scope` и с
  запрещённым `workflow`.

Общий дефект: doctors используют разрозненные ручные проверки вместо
authoritative schema плюс semantic/containment checks.

### PF-AUD-007 — неизменяемая версия процесса перезаписывается

Контракт `.pf/AGENTS.md` требует immutable process versions.
`command_process_authoring_apply` (`tools/processforge.py:11897-11956`) всегда
записывает process, prompt, docs и examples; collision/version guard отсутствует.

Два `process-create` с одним id и версией `1.0.0` оба возвращают 0; второй
меняет содержимое первой версии. Нужен отказ по умолчанию и отдельный
version-upgrade/явно одобренный override flow.

### PF-AUD-008 — creators допускают сущность, которую собственный doctor сразу отвергает

`run-create` и `task-create` не требуют существования process:
`require_official_process_active` возвращается без ошибки для неизвестного id
(`tools/processforge.py:10883-10902`, `16562-16568`, `16703-16710`).

`run-create --process does-not-exist --apply` пишет run и возвращает 0;
`run-doctor` сразу сообщает `FAIL: process exists`. Также можно создать run уже
со status `completed` без summary/handoff, который doctor немедленно отвергает.

Creator postcondition должна включать тот же полный invariant set, что и doctor,
до commit записи.

### PF-AUD-009 — context resolver скрывает неизвестный или inactive process

`build_execution_route` перехватывает `SystemExit` resolver и возвращает пустой
route без conflict (`tools/processforge.py:3792-3807`). Далее context получает
`status: resolved`.

Факт для `--process does-not-exist`:

```text
exit=0
status=resolved
conflicts=[]
execution_route.process=does-not-exist
stages=[]
```

Та же ветка применяется при построении project snapshot. Неразрешимый process
должен быть blocking conflict.

### PF-AUD-010 — failed platform остаётся `available` и `completed`

`platform-create` пишет contract и registry со status `available` до doctor
(`tools/processforge.py:19826-19843`), затем безусловно публикует
`platform.authoring.completed`.

При `--requires-package absent.package` команда вернула 1, но registry сохранил
доступную платформу, а event stream содержит `doctor.failed`, затем
`authoring.completed`.

Нужен transactional staging и commit только после doctor/review; при отказе —
никакой active registry entry.

### PF-AUD-011 — обновление knowledge manifest/index неатомарно

`write_package_manifest_and_index` сначала пишет manifest, затем index
(`tools/processforge.py:7512-7520`) без preflight, staging и rollback.

Если `indexes` занят обычным файлом, `knowledge-add-url --apply` падает с
`FileExistsError`, но новый resource уже находится в `package.yaml`.

### PF-AUD-012 — MCP master сохраняет literal secret

Документированный контракт запрещает хранить secrets напрямую. Реализация
проверяет `command`, но не `auth_ref` (`tools/processforge.py:20370-20383`), а
secret regex не распознаёт распространённый `sk-*`.

`--auth-ref sk-live-0123456789abcdef` записан в registry; и register, и
`doctor-workplace` вернули 0. Нужна строгая grammar ссылочного идентификатора и
secret scanning до proposal/write.

### PF-AUD-013 — CLI `tool-register`/`mcp-register` не реализует собственный process contract

Process definitions требуют registration request, provider definition,
validation report, review, blocking reviewed gate и healthcheck events.
CLI (`tools/processforge.py:20334-20403`) пишет proposal, registry, один общий
report и registered event; healthcheck, declared review/artifacts и blocking
review gate отсутствуют.

Либо CLI должен исполнять заявленный master, либо команды следует явно
позиционировать как низкоуровневую registry mutation, не как реализацию
governed process.

### PF-AUD-014 — consumer-mode не проверяет SHA-256 ZIP

`inspect_release_archive` сравнивает только список имён
(`tools/processforge.py:6038-6065`). SHA-256 сверяются только при наличии
optional `--root` (`6080-6117`).

Изменённый внутри копии ZIP `README.md` при неизменном manifest прошёл:

```text
release-archive-test --archive <tampered.zip> --extracted-test skip
RESULT: PASS
```

Получатель ZIP и manifest без source checkout не может доказать целостность.

### PF-AUD-015 — embedded checksums не покрывают весь release surface

Manifest/ZIP содержит 777 файлов, checksum inventory — 772. Не покрыты:

```text
.gitignore
AGENTS.md
QUICKSTART.ru.md
README.ru.md
checksums/processforge.sha256
```

Последний файл закономерно self-referential, но четыре остальных являются
поставляемой публичной поверхностью. Embedded checksum check всё равно PASS.

### PF-AUD-016 — linked launcher не восстанавливается через workplace/env после перемещения distribution

Generated launcher возвращает stale project-local `distribution_override`
раньше workplace registry и `PROCESSFORGE_HOME`
(`tools/processforge.py:2981-2996`).

После перемещения distribution и установки корректного `PROCESSFORGE_HOME`
launcher продолжает искать старый путь и завершается exit 1. Это противоречит
stable migration guide, где достаточно перепривязать workplace registry без
project migration.

### PF-AUD-017 — strict process collision не влияет на doctor result

Strict catalog создаёт warning
`requires process_override.reason` (`tools/processforge.py:10772-10791`), но он
остаётся только в JSON row и не входит в `report.checks`.

User-копия core process без override reason дала exit `0`, summary
`fail=0/warn=0`; collision виден только в `row.warnings`.

### PF-AUD-018 — release artifact не имеет проверяемого provenance

Текущий ZIP совпадает с dirty working tree, однако manifest хранит только
`name`, `version`, `generated_at`, `files`
(`tools/processforge.py:6016-6027`). Commit/tree id и dirty marker отсутствуют,
release gate не требует clean Git state.

До публикации нужен clean committed state и provenance в manifest либо
сопровождающем release attestation.

## 5. Medium и Low findings

### PF-AUD-019 — platform masters создают два конфликтующих layout

`platform-create` пишет
`platform-contracts/platform.<id>/platform-contract.yaml`, а
`platform-contract-install` — `platforms/<id>/platform.yaml`. Одинаковый id
молча переключает registry на второй путь, оставляя первый orphaned.

### PF-AUD-020 — lifecycle-команды допускают противоречивое частичное состояние

- `iteration-complete --status planned` ставит `completed_at`, оставляет status
  `planned` и публикует `iteration.failed`;
- `process-create` на неинициализированном root сначала пишет authoring session
  и event, затем падает на `require_flow_root`;
- dry-run `process-create` показывает только четыре private session files, но
  не перечисляет реальные public outputs apply.

### PF-AUD-021 — classifier/runtime-driver authoring и doctor coverage неполны

Для classifiers нет public create/register/doctor CLI; отсутствие или порча
registry не диагностируется workplace doctor. Для runtime drivers есть только
list/validate/describe, но нет create/register/validate-all.

Дополнительно list показывает same-id workplace driver как выбранный, а resolver
возвращает первый distribution match, то есть отображаемый provenance может не
совпадать с исполняемым.

### PF-AUD-022 — пустые tool/MCP definitions считаются здоровыми

Whitespace-only capability/command проходят register и `doctor-workplace`.
Семантическая валидация и healthcheck отсутствуют.

### PF-AUD-023 — чистый ZIP смешивает installation и неполный self-project

Packer синтезирует корневой `AGENTS.md` из `.pf/AGENTS.md`, но release ignore
удаляет assignments, contexts, artifacts, runtime, logs, reviews и handoffs.

- рабочая `.pf`: 723 файла;
- `.pf` чистого ZIP: 3 файла.

Корневой AGENTS требует active assignment/ECP/log/review/handoff, которых в
архиве нет. `doctor-project --project-root .` всё равно возвращает 0 с набором
WARN. Следует явно разделить distribution instructions и onboarded-project
instructions.

### PF-AUD-024 — documented first-run смешивает три корня

Installation guide сначала предлагает `cd process-forge`, затем first-run
использует `./pf-workplace` и `./my-project`. При буквальном copy/paste mutable
workplace и project создаются внутри заменяемой distribution directory, вопреки
linked-workplace model.

Также `first-run` не имеет `--profile`, поэтому documented
`generic-software-project` не активирует official software pack. Для production
profile требуется отдельный `workplace-init`.

### PF-AUD-025 — текущие release metadata не описывают release candidate

ZIP остаётся `1.0.0`, changelog не описывает current official bundled pack
slice, update index содержит placeholder `example.com` URLs. Перед публикацией
нужна осознанная версия, changelog и рабочие update metadata.

### PF-AUD-026 — public и project-local quality gates разошлись

Три последовательных dogfooding smoke:

```text
.pf/dogfooding/tests/scripts/smoke_resource_authoring_processes.py
.pf/dogfooding/tests/scripts/smoke_resource_management.py
.pf/dogfooding/tests/scripts/smoke_process_authoring.py
```

дали общий exit 1:

- resource management — PASS;
- full resource-authoring chain — FAIL на `project-onboard` из-за unresolved
  required capabilities;
- старый process-authoring smoke ждёт устаревший
  `processes/<id>.yaml` вместо `processes/user/<id>.yaml`.

Эти тесты не входят в public archive gate, поэтому полный release PASS скрывает
красное dogfooding. Тесты нельзя считать эквивалентом public release gate, но
перед релизом их нужно либо актуализировать, либо явно оформить waiver.

### PF-AUD-027 — `authoring-parity-check-all` имеет неполное штатное покрытие

Даже без искусственного FAIL штатный запуск выводит WARN и сообщает, что full
resource authoring round-trip пропущен для templates, knowledge packages и
platforms. Обнаружено и неотражённое поле
`runtime_execution_boundary` у `agent-director-supervision`.

### PF-AUD-028 — мелкие несогласованности

- `doctor-project` говорит `required capabilities are resolved or built in`,
  хотя built-in satisfaction удалена;
- proposal/report slug имеет точность только до секунды, поэтому одинаковые
  запросы в одну секунду могут перезаписать audit artifact.

## 6. Матрица мастеров сущностей

| Поверхность | Нормальный happy path | Негативные/контрактные проверки | Итог |
|---|---:|---:|---|
| workplace/project/first-run | PASS | registry completeness, boundary/profile — FAIL | Block |
| process create/apply/doctor | PASS | immutability, schema, partial state — FAIL | Block |
| run/task/iteration | PASS | unknown process, terminal state — FAIL | Block |
| knowledge package/resources | PASS | traversal, schema, atomicity — FAIL | Block |
| template create/doctor | PASS | schema/parity — FAIL | Block |
| platform create/install/doctor | PASS | failed commit, registry schema, dual layout — FAIL | Block |
| specialization create/doctor | PASS | traversal/schema — FAIL | Block |
| tool/MCP register | Basic write PASS | secrets, blanks, process gates/health — FAIL | Block |
| classifier | discovery работает | authoring/doctor отсутствуют | Incomplete |
| runtime driver | list/validate/describe работают | authoring/precedence/validate-all — FAIL | Incomplete |
| official process packs | normal activation/run PASS | missing activation registry/strict collision — FAIL | Block |
| release/archive | full extracted PASS | public-gate/tamper/provenance — FAIL | Block |

## 7. Что подтверждено рабочим

Следующие результаты являются положительными и не должны потеряться при
исправлении:

- source, ZIP и manifest совпадают: 777/777, file list и source-relative hashes
  PASS;
- full extracted `release-archive-test` — PASS, 510,49 с;
- forbidden archive entries — 0;
- private project/runtime `.pf` entries в ZIP — 0;
- official pack files — 30, legacy `examples/domain-packs/**` в ZIP — 0;
- case-insensitive duplicate paths — 0;
- private absolute path scan чист;
- schema validator текущего охваченного набора — PASS;
- embedded checksum inventory для охваченного набора — PASS;
- public cleanliness — PASS;
- обычные `workplace-init`, `project-onboard`, `first-run` и project launcher
  работают;
- пути с пробелами и кириллицей работают;
- `software-development` profile активирует official pack, официальный process
  запускается;
- inactive official process блокируется;
- process precedence project/user/custom над official/core работает;
- package-root resolver корректно обрабатывает объявленные root,
  writable/availability и дубликаты при нормальных canonical ids;
- нормальный platform doctor различает required FAIL и optional/recommended
  WARN;
- no-apply ресурсных команд действительно является dry-run/proposal mode;
- `git diff --check` прошёл.

## 8. Рекомендуемый порядок исправления

1. Закрыть оба path traversal общим canonical-id и containment primitive.
2. Исправить exit semantics двух aggregate gates и добавить deliberate-failure
   regression fixtures.
3. Принять ADR об authoritative schemas для package/template/platform registry.
4. Подключить schema validation ко всем creators/doctors и расширить release
   schema inventory на seeds/official knowledge manifests.
5. Сделать creator operations transactional: preflight, staging, doctor/review,
   atomic commit, rollback.
6. Восстановить process immutability и collision policy.
7. Исправить unknown/inactive process resolution в context/run/task flows.
8. Закрыть provider secret/blank/healthcheck/review contracts.
9. Исправить consumer ZIP hash verification, checksum release surface и
   provenance.
10. Исправить launcher relocation и installation/workplace/project docs.
11. Вернуть project-local dogfooding в зелёное состояние либо оформить
    осознанные waivers с причиной и сроком.
12. Собрать новый ZIP из clean commit и повторить весь набор проверок.

## 9. Обязательный retest перед релизом

- traversal attempts для package и specialization на Windows и POSIX separators;
- schema-invalid YAML/JSON и corrupt registries для каждого doctor;
- duplicate same-version process create;
- unknown/inactive process в context/run/task/project snapshot;
- failed platform и failed knowledge index write — отсутствие committed state;
- literal token и blank provider registration;
- aggregate parity с намеренным resource FAIL;
- `release-test --only public-gate` с намеренно сломанной schema/checksum;
- tampered ZIP с неизменным manifest без source root;
- relocation linked distribution через workplace registry и env fallback;
- clean-install paths: обычный, пробелы, кириллица, sibling workplace/project;
- полный public release test и полный extracted archive test;
- project-local resource/process authoring dogfooding без waiver.

## 10. Финальный вердикт

**NO-GO.** Архив технически собирается и проходит существующий full extracted
gate, но ядро пока не обеспечивает заявленные границы записи, неизменяемость,
schema authority, doctor reliability, transactional authoring и consumer-side
release integrity. Публикация текущего `dist/processforge.zip` создаст
неприемлемый риск повреждения workplace/project state и ложных зелёных
диагностик.
