# Independent integrated remediation review

- Проверено: `2026-07-30T07:34:54Z`
- Agent: `codex-remediation-first-review`
- Session: `pre-release-remediation-20260730-integrated-review`
- Lease: `lease-remediation-integrated-review-20260730`
- Assignment: `.pf/assignments/remediation-integrated-review-20260730.yaml`
- Scope: `PF-AUD-001—PF-AUD-006`
- Product tree: frozen, product writes запрещены
- Результат: **FAIL**

## Итог

Повторный интеграционный review подтверждает исправление обоих blocker из
первого review:

- конфликтующие `--only public-gate --skip public-gate` теперь дают nonzero и
  не запускают ни одной команды или public check;
- reusable-template v2 с обязательным, но пустым `files: []` проходит schema,
  а manifest без поля `files` отклоняется.

Также после freeze стали зелёными `template-create` + `template-doctor` и
`smoke_platform_create_include_levels.py`. Все dedicated security, schema,
aggregate, generator, doctor и registry smokes прошли.

Однако `PF-AUD-005` остаётся блокирующим: мастер
`knowledge-package-build-from-candidates` по-прежнему создаёт
schema-invalid manifest с `kind: knowledge_package`, печатает `BUILT` и
возвращает exit `0`. Следующий release/update-manifest flow принимает этот
результат. Поэтому интегрированный slice нельзя принять.

## Finding disposition

| Finding | Verdict | Evidence |
|---|---|---|
| `PF-AUD-001` | `fixed` | Security smoke проверил knowledge package path boundary, 23 unsafe IDs, dry-run/apply no-mutation, hub paths, valid dotted/dashed ID и внешний package root. |
| `PF-AUD-002` | `fixed` | Те же lexical и containment guarantees подтверждены для specialization create/lookup и escaping registry path. |
| `PF-AUD-003` | `fixed` | Aggregate smoke передаёт resource `FAIL` в nonzero общий result. |
| `PF-AUD-004` | `fixed` | Public group разворачивается, failure не скрывается; конфликтующий only/skip даёт exit `1`, calls `0`. |
| `PF-AUD-005` | **`partially_fixed, blocking`** | Template/platform/schema inventory исправлены, но knowledge hub builder создаёт запрещённый `kind: knowledge_package` и возвращает success. |
| `PF-AUD-006` | `fixed` | Doctors отклоняют invalid YAML/schema, не пишут events/snapshot; corrupt registries сохраняются byte-for-byte; independent tree fingerprints неизменны. |

## Blocking finding

### INT-REV-001 — knowledge hub создаёт и публикует schema-invalid package

Изолированный fixture использовал стандартную цепочку:

```text
evolve-candidate-create
  --project-root <temp>/project
  --workplace <temp>/workplace
  --from-file <candidate>

evolve-candidate-export
  --workplace <temp>/workplace
  --target docs.example
  --output <temp>/workplace/learning/bundles/learning-export-review.zip

knowledge-hub-init
  --hub <temp>/hub
  --apply

knowledge-hub-import
  --hub <temp>/hub
  --bundle <bundle>
  --apply

knowledge-package-build-from-candidates
  --hub <temp>/hub
  --package docs.example
  --version 1.1.0
  --apply
```

Команда build вернула:

```text
BUILD_EXIT=0
BUILT: <temp>/hub/packages/docs.example
```

Созданный `<temp>/hub/packages/docs.example/package.yaml`:

```yaml
schema_version: 1
id: docs.example
name: docs.example
version: 1.1.0
kind: knowledge_package
scope: workplace
```

Validation против authoritative
`schemas/package-manifest.schema.json` дала одну ошибку:

```text
$.kind: expected one of ['core', 'organization', 'direction',
'specialization', 'platform', 'toolchain', 'documentation', 'rules',
'source', 'mixed', 'project', 'process', 'task', 'agent_profile']
```

Причина видна в frozen source:

- `tools/processforge.py:13204` жёстко записывает
  `"kind": "knowledge_package"`;
- `tools/processforge.py:13210-13211` печатает `BUILT` и возвращает `0`;
- schema/doctor postcondition между записью и success отсутствует.

Это не только внутренний fixture defect:

```text
python tools/smoke_knowledge_package_release_update_manifest.py
PASS: knowledge package release update manifest smoke
```

Positive control строит тот же package, затем успешно создаёт ZIP и update
manifest. Следовательно, release surface не блокирует schema-invalid build.

Минимальный remediation scope:

1. выбрать разрешённый semantic kind из ADR по фактическому содержимому
   (`documentation`, `rules`, `source` или `mixed`);
2. валидировать staged/generated `package.yaml` authoritative schema до
   `BUILT` и exit `0`;
3. добавить в build и release smoke прямую проверку schema-valid manifest;
4. negative postcondition должен возвращать nonzero и не оставлять
   partially published package/release.

## Failed-review follow-ups

### Public-gate empty selection — PASS

Независимый synthetic fixture содержал одну public command.

```text
only = [public-gate]
skip = [public-gate]
EXIT=1
CALLS=0
FAIL: release-test selection resolved to no runnable checks
```

Не запускались ни release command, ни `public_release_checks`.

### Reusable-template empty files — PASS

```text
workplace v2 with files: []   errors=0
workplace v2 without files    errors=1
```

Обязательность поля сохранена, canonical ADR shape принят.

### Template create/doctor — PASS

Изолированный workplace:

```text
template-create exit=0
template-doctor exit=0
schema_version=2
type=reusable_template
schema_errors=0
```

### Platform include levels — PASS

```text
python tools/smoke_platform_create_include_levels.py
PASS: platform-create include levels
```

Synthetic platform registry теперь имеет обязательное `name`; required,
recommended и optional include levels сохранились.

## Independent tests

| Команда/проверка | Result |
|---|---|
| isolated public only/skip fixture | PASS contract: exit `1`, calls `0` |
| isolated reusable-template empty/missing files fixture | PASS |
| isolated template create + doctor + schema | PASS |
| isolated knowledge hub build + schema | **FAIL: blocker INT-REV-001** |
| `python tools/smoke_platform_create_include_levels.py` | PASS |
| `python tools/smoke_remediation_security_boundaries.py` | PASS, 63,5 с |
| `python tools/smoke_remediation_schema_inventory.py` | PASS |
| `python tools/smoke_remediation_aggregate_gates.py` | PASS |
| `python tools/smoke_remediation_generator_schema_alignment.py` | PASS |
| `python tools/smoke_remediation_doctor_contracts.py` | PASS |
| `python tools/smoke_remediation_registry_safety.py` | PASS |
| `python tools/smoke_knowledge_package_release_update_manifest.py` | PASS, но подтверждает отсутствие schema postcondition у release surface |
| `python tools/validate-process-forge-schemas.py` | PASS |
| targeted `python -m py_compile` | PASS |
| targeted `git diff --check` | PASS |

Full `release-test` не запускался по условиям assurance assignment.

## Mutation checks

Dedicated smokes подтвердили:

- unsafe package/specialization IDs отклоняются до proposal/event/file write;
- standalone template, knowledge, platform, specialization и process doctors
  не добавляют state-changing events;
- platform doctor не создаёт
  `artifacts/platform-stack.snapshot.yaml` и не меняет registry;
- `tool-register` при invalid YAML и wrong collection type возвращает nonzero
  и сохраняет registry byte-for-byte;
- invalid project/workplace YAML и отсутствие обязательного
  `process-packs.yaml` дают nonzero.

Дополнительно выполнен независимый fingerprint check полного временного tree:

```text
invalid package.yaml:
  knowledge-package-doctor exit=1
  tree unchanged=true

invalid registries/tools.yaml:
  doctor-workplace exit=1
  tree unchanged=true
  registry bytes preserved=true
```

То есть `PF-AUD-006` закрыт не только по exit code, но и по observational
no-mutation contract.

## Scope compliance

Product tree был объявлен frozen, активных parallel writers в assignment нет.
Reviewer выполнял записи только во временные каталоги и в два разрешённых
report path:

- `.pf/reviews/pre-release-remediation-integrated-review-20260730.md`;
- `.pf/artifacts/pre-release-remediation-agents/integrated-reviewer.md`.

Product code, schemas, packs, seeds и docs reviewer не изменял. Targeted
`git diff --check` для интегрированных product paths прошёл; предупреждения
Git касались только возможной будущей LF/CRLF normalization.

## Residual risks и решение

- Release остаётся **NO-GO** для этого slice до закрытия `INT-REV-001`.
- Dedicated generator smoke не покрывает knowledge hub builder; этот пробел
  позволил ему пройти при schema-invalid output.
- После узкого исправления требуется повторить isolated hub build/schema,
  build smoke и release/update-manifest smoke.
- Transactional authoring и остальные findings после `PF-AUD-006` не входят в
  этот review и не считаются проверенными.
