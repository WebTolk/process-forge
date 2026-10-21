# Scope and Acceptance

## In Scope
- Чтение и анализ `.pf/artifacts/`, `.pf/assignments/`, `.pf/runs/`, `.pf/handoffs/`, `.pf/logs/` по ключевым словам `hook`, `audit`, `outbox`.
- Проверка `.pf/hooks.yaml` и фактического состояния `.pf/runtime/hooks/outbox/wtaicc/`.
- Проверка кода доставки хуков: `src/processforge_core/raw_hook_journal.py`, `src/processforge_core/process_event_journal.py`, runtime hooks, `tools/pf_runtime/codex_hooks.py`.
- Запуск доступных smoke-тестов хуков (`tools/smoke_*.py`) в режиме только наблюдения/чтения, без изменения продукта.
- Запись артефактов:
  - `audit-findings.md`
  - `hook-outbox-status.md`
  - `hook-recovery-plan.md` (если требуется)

## Out of Scope
- Изменение продуктового кода без явного разрешения на стадии implementation.
- Удаление или изменение исторических PF-managed файлов (assignments, capsules, logs).
- Запуск инфраструктуры (Runtime, MCP, host hooks).

## Acceptance Criteria
- [x] PF context fresh и execution readiness ready.
- [ ] Список релевантных предыдущих Work с идентификаторами и статусами.
- [ ] Фактический статус outbox (пустой / есть события) и объяснение.
- [ ] Вывод о том, должны ли хуки записываться автоматически в текущей конфигурации.
- [ ] При отсутствии автозаписи: обоснованный план восстановления.
