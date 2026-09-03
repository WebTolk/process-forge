# Установка project-local Codex hooks

Дата: 2026-08-22

## Выполнено

- Проверен dry-run штатного opt-in installer.
- `tools/smoke_codex_integration.py` завершился PASS.
- Installer применён к project-local `.codex/hooks.json`; зарегистрированы все
  восемь наблюдательных событий: SessionStart, SessionEnd, PostToolUse,
  UserPromptSubmit, PreCompact, PostCompact, Stop и SubagentStop.
- Повторная проверка installer сообщила `complete: true`.
- Локальный файл hooks и его резервные копии исключены из Git, так как они
  содержат machine-local абсолютный путь к adapter'у.

## Граница

Конфигурация установлена только для данного проекта и не изменяет глобальный
Codex MCP config. Реальная загрузка hooks была проверена свежим Codex-сеансом
в следующем evidence шаге; его результат не подменяется успешной установкой.
