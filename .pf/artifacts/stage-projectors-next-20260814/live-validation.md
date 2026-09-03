# Живая проверка stage projector

Дата: 2026-08-14

## Сценарий

1. Поднят Runtime для `D:\.agents\processforge-workplace` на loopback `:8767`.
2. Созданы отдельные run/task `stage-projectors-live-proof-20260814` /
   `stage-projectors-live-hook-output`; ручной driver честно оставил Inspector
   state `manual_required`, поэтому для незакрытой задачи активна стадия
   `collect`.
3. Реальная сессия Codex `019ffed9-fa91-7901-a042-8d10875cc296` с моделью
   `gpt-5.3-codex-spark` через загруженные `.codex/hooks.json` создала ровно
   declared output `live-hook-output.md` shell-командой и выполнила
   `python tools/smoke_stage_projectors.py` (PASS).
4. Journal сохранил hook events `agent.session.started`, два
   `agent.command.completed` и `agent.session.ended`; source —
   `processforge.runtime.codex-hooks`.
5. Runtime scheduler автоматически пересобрал
   `.pf/artifacts/projections/stage-obligations.json`. Он содержит строку
   `process-supervisor:collect:required-output-readiness:stage-projectors-live-hook-output`
   со статусом `ready`, SHA-256 output и `status: current`.
6. После `runtime restart` тот же session routed к проекту; повторный
   `runtime work-state` и реальный stdio MCP вызов `pf.work_state` вернули ту
   же current projection. `runtime-host projection-doctor` прошёл.

## Границы доказательства

- Projection artifact не создавался и не правился вручную: только Runtime Host
  и его rebuild path владеют им.
- Проверка MCP read-only; существующий `smoke_runtime_ledger_hooks_mcp.py`
  также прошёл, включая изоляцию Ledger/MCP из предыдущего slice.
- Сразу после restart первый запрос work-state один раз превысил HTTP timeout,
  пока scheduler обрабатывал исторически большой проект; последующий запрос
  после scheduler pass успешен. Это не меняло durable state и не является
  основанием менять lifecycle в данном bounded slice.
