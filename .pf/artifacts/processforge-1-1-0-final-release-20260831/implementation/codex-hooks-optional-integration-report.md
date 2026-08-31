# Codex hooks как опциональная host-интеграция

## Реализованный контракт

- Generic `project-onboard` не создаёт `.codex/hooks.json`.
- Отсутствующие hooks имеют информационный статус
  `required: false`, `severity: info` и не переводят проект в `repairable`.
- Автоматический repair plan не содержит `install_codex_hooks`.
- Явное операторское действие `project-init-repair --repair-action
  install_codex_hooks --apply` сохранено и проверено.
- Повторное удаление hooks не меняет generic project readiness.
- Agent-инструкции начинают работу через `pf.context`, `pf.search`,
  `pf.resolve`, `pf.work.start` и запрещают обычному проектному агенту
  устанавливать или чинить Runtime/MCP/hooks/Ledger.

## Доказательство

`tools/smoke_project_init_codex_integration.py` прошёл полностью: onboarding
без hooks, explicit opt-in, installed status и последующий возврат к complete
без hooks.
