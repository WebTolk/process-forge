# Knowledge builder schema contract: отчёт реализации

- assignment: `remediation-knowledge-builder-contract-20260730`
- run: `pre-release-remediation-20260730`
- agent identity: `codex-remediation-generator-doctor`
- session: `pre-release-remediation-20260730-knowledge-builder`
- lease: `lease-remediation-knowledge-builder-20260730`
- status: `completed`
- finding: `PF-AUD-005`
- integrated blocker: `INT-REV-001`

## Root cause

`knowledge-package-build-from-candidates` жёстко записывал
`kind: knowledge_package`. Это структурное название сущности, которого нет в
semantic enum authoritative `package-manifest.schema.json`.

Build не выполнял schema postcondition, поэтому печатал `BUILT` и возвращал
exit `0`. `knowledge-package-release` также не валидировал существующий
`package.yaml`: он создавал ZIP, update manifest/index и затем изменял package
manifest.

## Выбор semantic kind

Выбран `kind: mixed`.

Hub build может одновременно содержать:

- reviewed candidates разных `category`;
- curated `candidate-notes.md`;
- incoming/unreviewed learnings, которые намеренно ещё не вошли в curated
  rules или documentation.

Без отдельного контентного classifier выбор `documentation`, `rules` или
`source` был бы недоказанным. `mixed` честно описывает агрегирующий build и
прямо разрешён ADR для hub generation, когда содержимое нельзя свести к одному
узкому виду.

## Build schema postcondition

Candidate package manifest теперь полностью строится в памяти в начале apply
path:

```yaml
schema_version: 1
id: docs.example
name: docs.example
version: 1.1.0
kind: mixed
scope: workplace
```

До первого `package_root` `mkdir` или resource write вызывается общий
`require_json_schema_document` с
`schemas/package-manifest.schema.json`. Schema failure блокирует build до
notes/index/package/changelog/release-plan mutation и до `BUILT`.

## Release rejection

`knowledge-package-release` до вычисления/создания output parent:

1. требует существующий `package.yaml`;
2. загружает его;
3. валидирует authoritative package schema;
4. проверяет совпадение manifest `id` с requested package id.

Только после успешного preflight разрешены ZIP и update metadata. Перед
финальной записью дополненного `package.yaml` manifest повторно проходит ту же
schema.

Negative regression подменяет `kind: mixed` на
`kind: knowledge_package` и подтверждает:

- release возвращает nonzero;
- output directory и ZIP отсутствуют;
- update manifest/index отсутствуют;
- tampered `package.yaml` сохранён byte-for-byte.

## RED -> PASS

До исправления новый targeted smoke дал все ожидаемые нарушения:

```text
built package is schema-invalid: $.kind expected one of authoritative enum
built package kind is not mixed: 'knowledge_package'
release accepted a schema-invalid package manifest
invalid release created ZIP output state
invalid release created update metadata
invalid release mutated package.yaml
```

После исправления:

```text
python tools/smoke_remediation_knowledge_builder_contract.py
PASS: knowledge builder/release schema contract smoke completed.
```

## Existing regressions

```text
python tools/smoke_knowledge_package_build_from_candidates.py
PASS: knowledge package build from candidates smoke

python tools/smoke_knowledge_package_release_update_manifest.py
PASS: knowledge package release update manifest smoke

python -m py_compile tools/processforge.py \
  tools/smoke_remediation_knowledge_builder_contract.py
PASS

python tools/validate-process-forge-schemas.py
PASS: ProcessForge structure and JSON Schema validation passed.

git diff --check -- tools/processforge.py \
  tools/smoke_remediation_knowledge_builder_contract.py
PASS
```

## Изменённые файлы

- `tools/processforge.py`
- `tools/smoke_remediation_knowledge_builder_contract.py`
- `.pf/artifacts/pre-release-remediation-agents/knowledge-builder-contract.md`

Schemas, docs, packs, seeds и existing smokes не изменялись.

## Residual risks

1. Автоматическое определение более узкого kind по candidate category/content
   не реализовано. Если продукту потребуется `documentation|rules|source`,
   это отдельная classifier/contract задача.
2. Полная transaction/rollback модель build/release находится вне этого
   bounded slice. Здесь закрыт заранее известный schema precondition и
   гарантировано отсутствие release mutation для invalid existing manifest.
3. Full release-test по assignment не запускался.

## Handoff

Integrated blocker `INT-REV-001` закрыт targeted evidence. Участок готов к
повторному независимому integrated review.
