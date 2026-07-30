# Generator/doctor CLI: отчёт реализации

- assignment: `remediation-generator-doctor-cli-20260730`
- run: `pre-release-remediation-20260730`
- agent identity: `codex-remediation-generator-doctor`
- session: `pre-release-remediation-20260730-generator-doctor`
- lease: `lease-remediation-generator-doctor-20260730`
- status: `completed`
- findings: `PF-AUD-005`, `PF-AUD-006`
- follow-up: минимальный selection fix для `PF-AUD-004`

## Результат

CLI generators и doctors синхронизированы с authoritative schemas из ADR.
Новая reusable template создаётся как schema v2, platform registry получает
полную identity-запись, invalid YAML больше не подменяется synthetic
manifest, corrupt registry не сбрасывается и не перезаписывается.

Standalone doctors в этом участке стали наблюдательными: они не пишут
resource events и platform snapshot. События, которые публикует creator после
явного вызова postcondition doctor, оставлены как события creator orchestration,
а не side effect standalone doctor.

## Generator schema postconditions

### Reusable template

`template-create` теперь записывает:

```yaml
schema_version: 2
type: reusable_template
```

Входы генератора приведены к schema-valid ids `project` и `scope`. Созданный
`template.yaml` проверяется `template-doctor` по
`schemas/reusable-template.schema.json`; legacy v1 остаётся читаемым и получает
migration `WARN`.

### Platform registry

Обе CLI-поверхности записи платформы формируют обязательные поля registry:

```yaml
id: audit
name: Audit Platform
package_id: platform.audit
path: platform-contracts/platform.audit/platform-contract.yaml
status: available
```

Для legacy `platform-contract-install`, где отдельного title argument нет,
`name` детерминированно строится из logical id. Registry update проходит
schema preflight до атомарной замены файла.

## Doctor layers

Добавлен общий `load_doctor_yaml`:

1. YAML parse;
2. non-empty object invariant;
3. authoritative JSON Schema;
4. существующие semantic/path/readiness checks.

Shipped schema validator внутри CLI расширен поддержкой `allOf`, `anyOf`,
`oneOf`, `not`, `if/then/else`, `uniqueItems` и `minProperties`.

Schema layer подключён к:

- knowledge packages — `package-manifest.schema.json`;
- reusable templates — `reusable-template.schema.json`;
- platform contracts — `platform-contract.schema.json`;
- specializations — `specialization.schema.json`;
- processes — `process-definition.schema.json`;
- project manifest — `process-forge-manifest.schema.json`;
- workplace manifest — `workplace.schema.json`;
- обязательным workplace registries, для которых опубликована schema.

`doctor-workplace` теперь требует `registries/process-packs.yaml`, проверяет
его YAML и list-shape, а также schema-validity distributions, platforms,
knowledge roots, package roots, template roots, tools и MCP registries.

Standalone knowledge/template/platform/process doctors больше не публикуют
state-changing success/failure events. Platform doctor вычисляет stack только
в памяти и не создаёт `artifacts/platform-stack.snapshot.yaml`.

## Invalid YAML и registry preservation

`load_workplace_package_manifest`:

- synthetic manifest создаёт только для отсутствующего package в поддерживаемом
  create/update flow;
- invalid YAML в read mode возвращает parse error doctor-слою;
- invalid YAML в write mode блокирует операцию вместо восстановления defaults.

`upsert_registry_entry` теперь:

- отказывает для directory вместо registry file;
- отказывает для invalid YAML;
- отказывает для empty/non-object registry;
- отказывает для существующей collection неправильного типа;
- проверяет schema всего registry после in-memory upsert;
- сохраняет исходный файл при любой preflight/schema ошибке;
- публикует valid update через same-directory temporary file и `os.replace`.

Отрицательный regression подтверждает byte-for-byte сохранность invalid YAML и
wrong-collection registry.

## PF-AUD-004 follow-up

По запросу orchestrator исправлен дополнительный false-green:

```text
release-test --only public-gate --skip public-gate
```

После фильтрации пустой runnable set теперь возвращает exit `1` с
`FAIL: release-test selection resolved to no runnable checks`, не запуская
release commands.

## Изменённые файлы

- `tools/processforge.py`
- `tools/smoke_remediation_generator_schema_alignment.py`
- `tools/smoke_remediation_doctor_contracts.py`
- `tools/smoke_remediation_registry_safety.py`
- `.pf/artifacts/pre-release-remediation-agents/generator-doctor-cli.md`

Schemas, docs, packs, seeds и `tools/validate-process-forge-schemas.py` в этом
lease не изменялись.

## Deliberate RED baseline

До изменения реализации три новых smoke дали ожидаемый результат:

```text
BASELINE generator=1 registry=1 doctors=1
```

- generator: template не соответствовал v2 и platform doctor писал snapshot;
- registry: invalid YAML сбрасывался и команда возвращала success;
- doctors: отсутствие `process-packs.yaml` не влияло на result.

## Targeted tests

После реализации:

```text
python tools/smoke_remediation_generator_schema_alignment.py
PASS: generator/schema alignment regression smoke completed.

python tools/smoke_remediation_registry_safety.py
PASS: registry safety regression smoke completed.

python tools/smoke_remediation_doctor_contracts.py
PASS: doctor contract regression smoke completed.

python -m py_compile tools/processforge.py \
  tools/smoke_remediation_generator_schema_alignment.py \
  tools/smoke_remediation_doctor_contracts.py \
  tools/smoke_remediation_registry_safety.py
PASS

python tools/validate-process-forge-schemas.py
PASS: ProcessForge structure and JSON Schema validation passed.

git diff --check -- <owned files>
PASS
```

Существующие targeted positive controls:

- `smoke_first_run.py` — PASS;
- `smoke_specialization_create_workplace_resource.py` — PASS;
- `smoke_process_authoring_writes_user_root.py` — PASS;
- `smoke_resource_versioning_modes.py` — PASS;
- specialization schema/registry/platform-binding/nested-workflow smokes —
  PASS;
- knowledge package build/release-update-manifest smokes — PASS;
- clean `platform-contract-install` + `doctor-workplace` — PASS.

## Residual risks

1. `smoke_platform_create_include_levels.py` был RED, потому что общий
   synthetic fixture создавал pre-ADR platform entry без обязательного `name`.
   Продуктовый upsert намеренно не мигрирует corrupt registry молча. Orchestrator
   передал исправление однофайлового fixture отдельному owner; повторный запуск
   ожидается после его handoff.
2. ADR показывает reusable v2 с `files: []`, но текущая authoritative schema
   требует `minItems: 1`. Generator создаёт один payload file и проходит schema;
   schema не менялась. Расхождение ADR/schema требует отдельного contract
   решения.
3. Transactional authoring, failed-platform rollback и legacy platform layout
   находятся в следующих remediation slices; этот участок не расширялся до
   полной transaction rewrite.
4. Полный `release-test` по ограничению assignment не запускался.

## Handoff

`tools/processforge.py` готов к freeze и независимому review. До объединения
следует повторить `smoke_platform_create_include_levels.py` после обновления
synthetic fixture, затем выполнить общий sequential integration set.
