# Ремедиация документации Runtime/MCP

## Статус

Выполнено.

## Измененные документы

- `docs/getting-started/runtime-autostart.md` — добавлена новая EN-страница про ручной Runtime lifecycle, Windows Task Scheduler autostart и host-owned Codex MCP stdio startup.
- `docs/ru/getting-started/runtime-autostart.md` — добавлена синхронная RU-страница.
- `docs/concepts/runtime-model.md` и `docs/ru/concepts/runtime-model.md` — разведены default file-first CLI runtime, optional Runtime Host ticks и optional long-lived PF Runtime service.
- `docs/concepts/runtime-mcp.md` и `docs/ru/concepts/runtime-mcp.md` — обновлена MCP-модель: Codex host владеет stdio process; список tools синхронизирован с кодом; mutating tools описаны как ограниченные governed actions с guard inputs.
- `docs/concepts/codex-session-read.md` — добавлены `pf codex-mcp status/install/remove` и явная граница host-owned stdio процесса.
- `docs/concepts/hooks-events.md` и `docs/ru/concepts/hooks-events.md` — уточнены boundaries hooks/outbox и capture semantics для `UserPromptSubmit`, `Stop.last_assistant_message`, `SubagentStop`.
- `docs/known-limitations.md` и `docs/ru/known-limitations.md` — заменено абсолютное “no daemon” на “no required daemon”; зафиксировано, что optional PF Runtime PoC/MVP и Windows autostart существуют, а watch-events/public API/web UI/database scheduler не реализованы.
- `docs/getting-started/installation.md` и `docs/ru/getting-started/installation.md` — удалена устаревшая ссылка на `v0.1`/абсолютное отсутствие background process, добавлена ссылка на autostart страницу.
- `docs/index.md` и `docs/ru/index.md` — добавлены ссылки на Runtime autostart и Runtime MCP.

## Сверка с executable behavior

- Runtime autostart описан как Windows per-user Task Scheduler logon task, запускающий `runtime serve` в foreground.
- Manual Runtime start описан как `runtime start`, который запускает detached background process.
- Codex MCP описан отдельно от Runtime autostart: registration управляется `pf codex-mcp`, а stdio process запускается Codex host.
- Для Runtime autostart отражены `status`, `install`, `remove`, `--apply`, `--replace`, `--force`, `--distribution-root`, `--python`, `--port`, `--interval`, `--delay-seconds`.
- Для Codex MCP отражены `status`, `install`, `remove`, `--apply`, `--replace`, `--force`, `--name`, `--python`, `--codex`, `--distribution-root`.

## Проверки

- `rg` по целевым устаревшим утверждениям: совпадений не найдено.
- `git diff --check` по измененным docs/artifact файлам: без ошибок.

## Остаточные риски

- Полный markdown link checker не запускался.
- Кодовые файлы не изменялись по условиям assignment.