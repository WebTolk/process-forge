# Task Record: Аудит предыдущей работы ProcessForge и проверка хуков outbox

## Objective
Провести аудит предыдущей работы по проекту ProcessForge с фокусом на автоматическую запись хуков PF в outbox, проверить их наличие и, при необходимости, восстановить доставку согласно проектной политике.

## Scope
- `.pf/artifacts/`, `.pf/assignments/`, `.pf/runs/`, `.pf/handoffs/`, `.pf/logs/` — историческая работа и артефакты.
- `.pf/hooks.yaml` и `.pf/runtime/hooks/outbox/wtaicc/` — конфигурация и фактические хуки.
- `src/processforge_core/**/*.py` — hook/event journal/runtime модули, участвующие в доставке.
- `tools/pf_runtime/codex_hooks.py`, `tools/smoke_*.py`, `tests/**/*.py` — инструменты и тесты хуков.

## Deliverables
- `.pf/artifacts/processforge-pf-outbox-2/audit-findings.md`
- `.pf/artifacts/processforge-pf-outbox-2/hook-outbox-status.md`
- `.pf/artifacts/processforge-pf-outbox-2/hook-recovery-plan.md` (при необходимости)

## Mode
Assurance/verification только для аудита; изменения кода только после явного разрешения на стадии implementation.
