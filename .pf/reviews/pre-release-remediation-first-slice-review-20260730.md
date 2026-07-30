# Independent review: first pre-release remediation slice

- Дата проверки: `2026-07-30T07:16:23Z`
- Reviewer: `codex-remediation-first-review`
- Session: `pre-release-remediation-20260730-first-review`
- Lease: `lease-remediation-first-review-20260730`
- Assignment: `.pf/assignments/remediation-first-slice-review-20260730.yaml`
- Проверяемый scope: `PF-AUD-001—PF-AUD-005`
- Результат: **FAIL**

## Итог

Первый remediation slice нельзя принять как завершённый. Исправления
`PF-AUD-001—PF-AUD-003` подтверждены независимыми негативными и
регрессионными проверками. `PF-AUD-004` исправлен частично:
`public-gate` разворачивается и передаёт failure, однако противоречащая
комбинация `--only public-gate --skip public-gate` оставляет пустую выборку и
возвращает exit `0`. `PF-AUD-005` также закрыт лишь частично: восемь knowledge
manifest поставлены под schema gate, dotted/dashed ID и package kinds
согласованы, но reusable-template schema противоречит принятому ADR.

Два подтверждённых блокера относятся к уже замороженным slices и не зависят от
параллельной работы:

1. `release-test` не проверяет пустую выборку после применения `--skip`;
2. `reusable-template.schema.json` запрещает canonical `files: []`, разрешённый
   принятым ADR.

## Finding disposition

| Finding | Verdict | Независимое основание |
|---|---|---|
| `PF-AUD-001` | `fixed` | 23 unsafe ID варианта отклонены в dry-run и apply без proposal/event/file mutation; hub build/release также отклоняют traversal; dotted/dashed ID и внешний зарегистрированный package root работают. |
| `PF-AUD-002` | `fixed` | Та же централизованная ID/containment boundary проверена для specialization create/read paths, Windows devices и escaping registry path. |
| `PF-AUD-003` | `fixed` | Искусственный resource `FAIL` при process `PASS` даёт nonzero aggregate result. |
| `PF-AUD-004` | `partially_fixed` | Expansion и intentional public command failure работают, но `--only public-gate --skip public-gate` возвращает `0` при фактически пустой выборке. |
| `PF-AUD-005` | `partially_fixed` | Package schema/inventory и discriminator-based template split подтверждены; reusable v2 `files` contract противоречит ADR. Полный creator → schema → doctor round-trip не может считаться закрытым до интеграционного повторного теста. |

## Подтверждённые блокеры

### REV-FIRST-001 — empty public selection после `--skip` возвращает PASS

Принятый ADR, Decision 7, требует configuration `FAIL`, если selection
случайно стала пустой. В `command_release_test` проверка пустой selection
выполняется сразу после `--only`, до применения `--skip`. После удаления
`public_gate=true` команд повторной проверки нет.

Изолированный тест с одной synthetic public command:

```text
only = [public-gate]
skip = [public-gate]
executed commands = 0
public checks = 0
EXIT=0
RESULT: PASS with warnings
```

Это оставляет ложнозелёный путь у `PF-AUD-004`. Требуется выполнять final
non-empty selection validation после композиции `--only` и `--skip` и добавить
этот случай в `smoke_remediation_aggregate_gates.py`.

### REV-FIRST-002 — canonical `files: []` отвергается reusable-template schema

ADR `.pf/adr/pre-release-remediation-schema-authority-20260730.md:112-123`
объявляет workplace manifest v2 authoritative и приводит required shape с
`files: []`. Schema `schemas/reusable-template.schema.json:41-56`, свойство
`files` на строке 55, устанавливает `minItems: 1`.

Независимая validation canonical prompt-template shape:

```text
schema_version: 2
type: reusable_template
id: new.empty
kind: prompt
files: []

result: FAIL
$: expected exactly one oneOf alternative, got 0
```

Authority трактуется так: поле `files` обязательно, но пустой массив допустим.
Это также необходимо для `prompt` и `media_prompt`, у которых может не быть
file mapping. Требуется убрать `minItems: 1` и добавить positive test для
`files: []`. Если продукт намерен требовать хотя бы один file для всех kinds,
сначала требуется follow-up ADR и изменение canonical snippet.

## Independent tests

| Проверка | Результат |
|---|---|
| `python tools/smoke_remediation_security_boundaries.py` | PASS, 64,2 с |
| `python tools/smoke_remediation_schema_inventory.py` | PASS |
| `python tools/smoke_remediation_aggregate_gates.py` | PASS, но smoke не покрывает `--only public-gate --skip public-gate` |
| isolated `--only public-gate --skip public-gate` fixture | **FAIL contract:** product exit `0` |
| reusable-template oneOf discriminator fixture | PASS: v1 и v2 с пересекающимися extra fields совпадают ровно с одной веткой; manifest без discriminator отклонён |
| reusable-template v2 `files: []` fixture | **FAIL contract:** canonical ADR shape отклонён |
| `python tools/validate-process-forge-schemas.py` | PASS |
| `python tools/smoke_specialization_registry.py` | PASS |
| `python tools/smoke_knowledge_hub_import.py` | PASS |
| `python tools/smoke_knowledge_package_build_from_candidates.py` | PASS функционального smoke |
| `python -m py_compile` для CLI, validator и трёх remediation smokes | PASS |
| `git diff --check` для frozen owned files | PASS |

Security smoke проверяет 23 path-like/unsafe ID, оба entity masters, dry-run и
apply, control characters, percent/double-percent encodings, Windows reserved
devices (`con`, `prn`, `aux`, `nul`, `com1..9`, `lpt1..9`), отсутствие
мутаций, registry path containment, hub build/release, valid external package
root и сохранение dotted/dashed IDs.

Schema inventory проверяет точное множество 8 manifest:

- 6 `packs/official/software-development/knowledge-packages/*.yaml`;
- 2 `seeds/knowledge-packages/*.yaml`.

Удаление или появление лишнего manifest меняет discovered set и делает smoke
красным. Все восемь входят также в `REQUIRED_FILES` release validator.

## Наблюдения на незамороженном integration tree

Во время review соседний `generator-doctor` writer продолжал изменять общий
`tools/processforge.py`. Поэтому следующие результаты являются важным
integration evidence, но должны быть повторены после его handoff:

- `template-create` записал entity, затем вернул exit `1`; doctor сообщил
  `expected exactly one oneOf alternative, got 0`;
- `knowledge-package-build-from-candidates` вернул `0`, но созданный
  `package.yaml` содержал `kind: knowledge_package` и не прошёл authoritative
  package schema;
- `python tools/smoke_platform_create_include_levels.py` завершился exit `1`,
  потому что strict registry preflight отверг legacy fixture entry без `name`.

Эти результаты подтверждают, что end-to-end часть `PF-AUD-005` на момент
наблюдения ещё не была интеграционно зелёной. Они не используются для
атрибуции дефекта конкретному frozen writer.

## Compatibility

- Dotted и dashed package/specialization IDs сохранены.
- Registered external package root остаётся допустимым и containment
  проверяется относительно объявленного root.
- Reusable-template `oneOf` не имеет двусмысленности: `schema_version` с
  `const: 1|2` является достаточным discriminator в shipped validator.
- Legacy reusable v1 и portable template package остаются различимыми.
- Полная platform/template/hub compatibility требует повторного запуска после
  завершения активного generator-doctor slice.

## Scope compliance

По assignments и implementation reports оба frozen writer заявили только
разрешённые файлы:

- critical CLI: `tools/processforge.py`, два remediation smoke и собственный
  report;
- schema alignment: четыре schema, schema validator, schema inventory smoke и
  собственный report; shipped manifests не переписывались.

Прямых признаков записи critical writer в schemas/docs или schema writer в
`tools/processforge.py` не обнаружено. Однако repository не имеет отдельного
commit на каждый lease, а общий dirty tree изменялся следующим sole writer во
время review. Поэтому файловую атрибуцию нельзя доказать одним `git diff`;
scope verdict: `pass_with_conditions`, с опорой на Agent Ledger, assignments и
reports.

Сам reviewer изменил только два пути, разрешённых его assignment:

- `.pf/reviews/pre-release-remediation-first-slice-review-20260730.md`;
- `.pf/artifacts/pre-release-remediation-agents/first-slice-reviewer.md`.

## Условия повторного review

1. Исправить final empty-selection check и добавить regression для
   `--only public-gate --skip public-gate`.
2. Привести reusable-template schema к ADR: required `files`, empty allowed;
   добавить positive/negative schema cases.
3. После handoff generator-doctor writer повторить template create/doctor,
   knowledge hub build/schema validation и platform create regression.
4. Не запускать full release до зелёного targeted review; полный source и
   extracted archive gate остаются обязанностью интеграционного этапа.
