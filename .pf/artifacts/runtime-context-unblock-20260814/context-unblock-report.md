# Context unblock для PF Runtime

- date: `2026-08-14`
- run: `runtime-context-unblock-20260814`
- assignment: `runtime-context-unblock`

## Причина

Snapshot от 13 августа был построен с установленным workplace и активным
`processforge.official.software-development` pack. Текущий project check при
`workplace.reference: auto` не знал private workplace manifest, поэтому не
загружал classifiers, видел проект как `unclassified` и не находил capability
providers только из project registry.

## Исправление

- Добавлен ignored `.pf/process-forge.local.yaml` с private ссылкой на уже
  установленный local workplace. Shared workplace и его pack registry не менялись.
- Project registry теперь явно объявляет доступные providers:
  `repository_read`, `markdown_editing`, `schema_validation`.
- Контекст обновлён, новый snapshot: `ctx-20260814-035156-d5d5ac`.

## Проверка

- `project-context-check --project-root .`: `STATUS: fresh`, `POLICY_ACTION: continue`.
- `assignment-capsule` для ранее заблокированного review assignment успешно создал
  immutable capsule.
- `validate-process-forge-schemas.py --root .`: PASS.

## Остаточные долги

- `project-context-refresh` записывает fresh snapshot, но возвращает exit code 1;
  это CLI inconsistency, которую нужно исследовать отдельно.
- `doctor-project` остаётся FAIL по историческим onboarding artefacts и отсутствию
  `.pf/runtime/bin/pf.py`; это не блокирует context check/capsule, но должно быть
  отдельным onboarding-recovery slice.
