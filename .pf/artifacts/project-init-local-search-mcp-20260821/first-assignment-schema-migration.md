# Миграция onboarding first-assignment к task schema

Дата: 2026-08-21

Текущий `.pf/assignments/first-assignment.yaml` и генератор onboarding в
`tools/processforge.py` приведены к обязательной форме task schema: добавлены
`run_id`, пустой `iterations` и начальный `result` со статусом `pending`.
Идентификатор run в генераторе формируется от onboarding defaults, поэтому
сохраняет intent конкретного нового проекта.

Проверка: `python tools/validate-process-forge-schemas.py --root .` — PASS.
