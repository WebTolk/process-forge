# Schema alignment: отчёт реализации

- assignment: `remediation-schema-alignment-20260730`
- run: `pre-release-remediation-20260730`
- agent identity: `codex-remediation-schema`
- session: `pre-release-remediation-20260730-schema`
- lease: `lease-remediation-schema-20260730`
- completed_at: `2026-07-30T06:49:57Z`
- status: `completed`
- primary finding: `PF-AUD-005`

## Применённые решения schema authority

1. Общая грамматика resource id зафиксирована как
   `^[a-z][a-z0-9]*(?:[.-][a-z0-9]+)*$`.
2. `package-manifest.schema.json` остаётся authoritative contract для knowledge
   package:
   - сохранены все прежние значения `kind`;
   - добавлены поддерживаемые мастером `rules`, `source`, `mixed`;
   - `knowledge_package` намеренно не добавлен.
3. Template contracts разведены:
   - legacy reusable manifest v1 продолжает приниматься с
     `source_package` и `type`;
   - workplace reusable manifest v2 требует
     `schema_version: 2`, `type: reusable_template`, `id`, `title`, `kind`,
     `version`, `files`;
   - portable `template-package.yaml` остаётся отдельным contract и принимает
     общую dotted/dashed id grammar.
4. Platform registry entry требует полный набор:
   `id`, `name`, `path`, `package_id`, `status`.

## Изменённые файлы

- `schemas/package-manifest.schema.json`
- `schemas/reusable-template.schema.json`
- `schemas/template-package.schema.json`
- `schemas/platform-registry.schema.json`
- `tools/validate-process-forge-schemas.py`
- `tools/smoke_remediation_schema_inventory.py`

`tools/processforge.py`, docs и templates не изменялись в этом lease.

## Resources migrated

Физического переименования или переписывания manifests не потребовалось.
Утверждённый contract сохраняет существующие canonical ids.

Под обязательную schema validation поставлены восемь ранее пропускавшихся
resources:

- 6 manifests из
  `packs/official/software-development/knowledge-packages/*.yaml`;
- 2 manifests из `seeds/knowledge-packages/*.yaml`.

Все восемь проходят обновлённую package schema. Их paths также добавлены в
обязательный release inventory, поэтому удаление одного из них теперь является
ошибкой структуры, а не молчаливым уменьшением glob-набора.

## Validation coverage

`validate-process-forge-schemas.py` теперь проверяет:

- root `packages/*.yaml`;
- official bundled knowledge manifests;
- seed knowledge manifests;
- `templates/template-package.yaml`;
- `templates/registries/platforms.yaml`;
- существующие official process-pack/process/classifier surfaces.

Новый `smoke_remediation_schema_inventory.py` проверяет:

- полный inventory 6 official + 2 seed manifests;
- positive dotted/dashed ids и весь утверждённый package `kind` enum;
- negative `knowledge_package`, traversal/path-like и некорректные ids;
- positive reusable template v1 и workplace v2;
- разделение reusable и portable template contracts;
- обязательность всех пяти platform registry fields;
- наличие новых mappings и manifests в release validator inventory.

## Tests

Выполнено последовательно:

```text
python tools/smoke_remediation_schema_inventory.py
PASS: remediation schema inventory smoke completed.

python tools/validate-process-forge-schemas.py
PASS: ProcessForge structure and JSON Schema validation passed.

python -m py_compile tools/validate-process-forge-schemas.py tools/smoke_remediation_schema_inventory.py
PASS (exit 0)

git diff --check -- <owned schema/validator files>
PASS (exit 0)
```

Полный `release-test` по условиям assignment не запускался.

## Residual risks и интеграционные зависимости

1. Текущий на момент начала lease `template-create` ещё записывал legacy-like
   manifest с `schema_version: 1`, но без v1-required `source_package/type`.
   Соседний CLI slice должен перевести generator на утверждённый workplace v2.
   Repository schema gate остаётся зелёным, поскольку такого generated fixture
   в release tree нет.
2. Текущий `platform-create` на момент исследования не записывал registry
   `name`. Соседний CLI slice обязан сформировать все пять required fields до
   подключения schema-validation doctor layer.
3. Doctors и runtime generator validation находятся вне этого write scope;
   этот slice предоставляет им authoritative schemas и inventory, но сам
   `tools/processforge.py` не меняет.
4. В окружении отсутствует сторонний пакет `jsonschema`; проверки выполнялись
   shipped custom Draft-2020 subset validator. Схемы используют только
   поддерживаемые им keywords (`oneOf`, `$ref`, `const`, `enum`, `required`,
   `type`, `pattern`, `minLength`, `minItems`).

## Итог

Schema authority и release inventory для PF-AUD-005 приведены в согласованное,
backward-compatible состояние. Slice готов к интеграционному review после
синхронизации CLI generators/doctors с v2 reusable template и полным platform
registry entry.
