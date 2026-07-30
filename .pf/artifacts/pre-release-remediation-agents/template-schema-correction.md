# Reusable-template empty-files correction

- assignment: `remediation-template-schema-correction-20260730`
- run: `pre-release-remediation-20260730`
- agent: `codex-remediation-schema`
- session: `pre-release-remediation-20260730-template-schema`
- lease: `lease-remediation-template-schema-20260730`
- completed_at: `2026-07-30T07:21:39Z`
- status: `completed`

## Contradiction

ADR `pre-release-remediation-schema-authority-20260730.md:112-123` определяет
authoritative workplace reusable-template v2 и явно приводит required поле:

```yaml
files: []
```

В `schemas/reusable-template.schema.json` поле `files` одновременно было
required и имело `minItems: 1`. Поэтому нормативный ADR fixture отвергался
схемой.

## Change

Из `workplaceV2.properties.files` удалено только ограничение `minItems: 1`.

Сохранены:

- обязательность самого поля `files`;
- тип `array`;
- schema validation каждого существующего элемента через `$defs/file`;
- version-dispatch между legacy v1 и workplace v2;
- все остальные identity и kind constraints.

CLI, release validator, docs и templates не изменялись.

## Positive and negative tests

В `tools/smoke_remediation_schema_inventory.py` добавлен отдельный positive
fixture workplace v2 с `files: []`.

Существующий negative fixture без поля `files` сохранён. Таким образом,
регрессия различает два контракта:

- поле присутствует и массив пуст — `PASS`;
- поле отсутствует — `FAIL`.

Выполнено:

```text
python tools/smoke_remediation_schema_inventory.py
PASS: remediation schema inventory smoke completed.

python tools/validate-process-forge-schemas.py
PASS: ProcessForge structure and JSON Schema validation passed.

python -m py_compile tools/smoke_remediation_schema_inventory.py
PASS (exit 0)

git diff --check -- schemas/reusable-template.schema.json tools/smoke_remediation_schema_inventory.py
PASS (exit 0)
```

## Residual risks

- Published/catalog reusable templates могут нуждаться в отдельном semantic
  doctor requirement для `source_package`; ADR оставляет его optional для
  workplace-local authoring, поэтому это не должно кодироваться как общий
  schema-required field.
- Пустой `files` теперь нормативно допустим, но readiness конкретного kind
  может позднее вводить дополнительные semantic checks. Это не должно снова
  противоречить общему v2 manifest contract.

## Итог

Независимо найденное противоречие устранено минимальным изменением. Поле
`files` осталось обязательным, нормативный `files: []` проходит, отсутствие
поля блокируется.
