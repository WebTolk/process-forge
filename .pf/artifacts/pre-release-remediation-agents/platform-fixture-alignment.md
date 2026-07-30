# Отчёт: выравнивание synthetic platform fixture

Дата: 2026-07-30
Assignment: `remediation-platform-fixture-alignment-20260730`
Agent Ledger: `codex-remediation-fixture` / `pre-release-remediation-20260730-fixture` / `lease-remediation-platform-fixture-20260730`

## Fixture contract

В `tools/core_boundary_smoke_helpers.py` synthetic-запись
`registries/platforms.yaml` приведена к принятому в ADR и
`schemas/platform-registry.schema.json` контракту identity:

```yaml
id: example
name: Example
package_id: platform.example
path: platform-contracts/platform.example/platform-contract.yaml
status: available
```

Изменение ограничено добавлением обязательного `name`. Product validation,
safe-upsert, CLI, schemas и пользовательские/legacy registries не изменялись.
Это сохраняет требуемое поведение: corrupt реальные данные отклоняются, а
тестовый workplace изначально создаётся валидным.

## Affected tests

Исправлен общий fixture, который использует
`tools/smoke_platform_create_include_levels.py`. Smoke проверяет успешное
создание дочернего platform contract и сохранение трёх уровней зависимостей:
required knowledge packages, recommended templates и optional tools.

## Tests

```text
python -m py_compile tools/core_boundary_smoke_helpers.py
PASS

git diff --check -- tools/core_boundary_smoke_helpers.py
PASS

python tools/smoke_platform_create_include_levels.py
PASS: platform-create include levels
```

Scoped diff содержит одну функциональную строку: `name: Example`.

## Residual risks

- Проверялся только назначенный platform-create integration smoke; полный
  release suite остаётся обязанностью orchestrator после объединения всех
  remediation slices.
- Исправление не мигрирует уже существующие registries без `name`; по ADR это
  намеренное ограничение safe-upsert, а не задача fixture-maintenance.
- Git предупредил о возможной будущей нормализации LF в CRLF рабочим Git,
  однако `git diff --check` прошёл, а фактический diff не содержит массовой
  смены окончаний строк.
