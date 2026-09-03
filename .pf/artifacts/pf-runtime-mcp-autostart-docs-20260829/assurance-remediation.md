# Ремедиация assurance finding: Codex MCP Python drift

## Статус

Выполнено.

## Исправление

- Режим по умолчанию принимает совместимые Python launcher names для уже
  существующих Codex registrations.
- Явный `--python` теперь включает строгое сравнение команды, включая
  нормализованное сравнение путей.
- Smoke покрывает compatible default launcher, mismatch explicit pin и exact
  explicit pin.
- EN/RU документация явно описывает точный контракт `--python`.
