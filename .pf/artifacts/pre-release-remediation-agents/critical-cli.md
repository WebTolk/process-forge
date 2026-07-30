# Critical CLI remediation report

- Дата: 2026-07-30
- Агент: `codex-remediation-critical-cli`
- Сессия: `pre-release-remediation-20260730-critical-cli`
- Lease: `lease-remediation-critical-cli-20260730`
- Assignment: `.pf/assignments/remediation-critical-cli-20260730.yaml`
- Scope: `PF-AUD-001—004`
- Статус: implementation complete, ready for independent review

## Результат

Закрыт первый critical remediation slice:

| Finding | Disposition | Реализация |
|---|---|---|
| `PF-AUD-001` | fixed, targeted tests pass | Строгая проверка knowledge-package ID до proposal/event/write; containment после resolve во всех общих package resolvers, create, hub build и release. |
| `PF-AUD-002` | fixed, targeted tests pass | Строгая проверка specialization ID до proposal/write; containment create/candidate paths и registry paths под объявленным `PF_SPECIALIZATIONS`. |
| `PF-AUD-003` | fixed, targeted tests pass | `authoring-parity-check-all` возвращает nonzero при агрегированном `FAIL`, а не только при process failure. |
| `PF-AUD-004` | fixed, targeted tests pass | `public-gate` разворачивается во все команды с `public_gate=true` и запускает public checks; пустая `--only`-выборка является ошибкой. |

## Реализованные контракты

В `tools/processforge.py:448-485` добавлена единая boundary-проверка:

- authoritative grammar: `^[a-z][a-z0-9]*(?:[.-][a-z0-9]+)*$`;
- dotted и dashed ID сохраняются без `safe_id` normalization;
- до любой записи отклоняются separators, drive/UNC/colon syntax, whitespace и control characters, dot-segments, percent encoding и Windows trailing dot/space;
- отклоняются Windows reserved device basenames: `con`, `prn`, `aux`, `nul`,
  `com1..9`, `lpt1..9`, в том числе перед расширением;
- после построения target выполняется `Path.resolve()` и containment под declared root;
- зарегистрированный внешний package root остаётся допустимым: containment выполняется под ним, а не принудительно под workplace.

Проверка подключена к следующим поверхностям:

- specialization registry/candidate resolvers: `tools/processforge.py:3567-3633`;
- package path/write/read resolvers: `tools/processforge.py:6918-6942`;
- resource index fallback: `tools/processforge.py:7575-7587`;
- knowledge hub build/release: `tools/processforge.py:13109-13173`;
- `knowledge-package-create`: `tools/processforge.py:19830-19849`;
- `specialization-create`: `tools/processforge.py:20617-20631`.

Aggregate gate исправлен в `tools/processforge.py:13835-13871`.
Synthetic release group исправлен в `tools/processforge.py:5951-5993`.

## Negative tests: red до исправления

Созданы:

- `tools/smoke_remediation_security_boundaries.py`;
- `tools/smoke_remediation_aggregate_gates.py`.

Зафиксированный baseline:

1. Security smoke завершался с exit `1`: `knowledge-package-create` принимал
   `../escaped` в dry-run и записывал proposal.
2. Aggregate smoke завершался с exit `1`: смоделированный resource `FAIL`
   попадал в summary, но `authoring-parity-check-all` возвращал `0`.

## Targeted verification: green после исправления

```text
python -m py_compile tools/processforge.py tools/smoke_remediation_security_boundaries.py tools/smoke_remediation_aggregate_gates.py
PASS

python tools/smoke_remediation_security_boundaries.py
PASS: remediation resource authoring security boundaries

python tools/smoke_remediation_aggregate_gates.py
PASS: remediation aggregate gates
```

Security smoke покрывает:

- 23 unsafe ID variants;
- dry-run и apply для обоих entity masters;
- отсутствие proposal/event/file mutation до reject;
- percent-encoded и double-encoded separators;
- control characters;
- Windows reserved device basenames;
- hub build/release;
- specialization registry path escape;
- валидные dotted/dashed IDs;
- валидный зарегистрированный внешний package root.

Aggregate smoke покрывает:

- resource failure при successful process parity;
- фактическое разворачивание `public-gate`;
- исключение `public_gate=false` команды;
- intentional failure public-команды;
- fail на пустой synthetic group.

Регрессионные smokes:

```text
python tools/smoke_specialization_create_workplace_resource.py
PASS: smoke_specialization_create_workplace_resource

python tools/smoke_specialization_registry.py
PASS: smoke_specialization_registry

python tools/smoke_specialization_context_resolution.py
PASS: smoke_specialization_context_resolution

python tools/smoke_specialization_platform_binding.py
PASS: smoke_specialization_platform_binding

python tools/smoke_knowledge_hub_import.py
PASS: knowledge hub import smoke

python tools/smoke_knowledge_package_build_from_candidates.py
PASS: knowledge package build from candidates smoke

python tools/smoke_knowledge_package_release_update_manifest.py
PASS: knowledge package release update manifest smoke
```

Read-only release listing:

```text
python bin/pf.py release-test --root . --list
exit=0
public_gate=true commands=137
public-gate labels=1
git diff --check labels=1
```

`git diff --check` для owned files ошибок не выявил.

## Изменённые файлы

- `tools/processforge.py`
- `tools/smoke_remediation_security_boundaries.py`
- `tools/smoke_remediation_aggregate_gates.py`
- `.pf/artifacts/pre-release-remediation-agents/critical-cli.md`

Schemas, docs, validators, packs и seeds не изменялись.

## Residual risks и следующий gate

- Полный `release-test --public` и extracted archive test намеренно не запускались:
  assignment запрещал полный release-test, их должен выполнить оркестратор после
  интеграции остальных remediation slices.
- Новые smoke-файлы пока являются targeted remediation evidence; решение о
  включении их в постоянный public release command catalog должен принять
  интеграционный reviewer после schema-alignment slice.
- Проверка package version и произвольного `--output` у knowledge-package release
  не входила в `PF-AUD-001—004`; `--output` остаётся явно управляемым путём
  оператора.
- Независимый reviewer должен подтвердить `--only/--skip` composition и отсутствие
  конфликтов с параллельными schema/contract изменениями.
