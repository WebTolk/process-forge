# Реализация: Ledger-centric Runtime, Codex hooks и read-only MCP

## Результат

Реализован ограниченный срез без второй модели PF Core:

- Agent Ledger стал источником маршрута `session -> project`.
- `runtime/pf-runtime-host/state.json.sessions` явно помечается только как
  `cache_only`; его удаление больше не лишает Runtime маршрута.
- Ledger presence теперь сохраняет `project_root` вместе с `project_id`.
- Session registration использует тот же Core путь `agent.session.started`,
  который создаёт Ledger check-in.
- Codex adapter нормализует документированные `SessionStart`, `SessionEnd` и
  `PostToolUse`; он не исполняет payload и при не-PF `cwd` возвращает успех.
- Добавлен stdio MCP facade с `pf.project_state`, `pf.work_state`,
  `pf.resolve` и `pf.workplace_state`. Он требует уже существующую Ledger
  session и не создаёт отдельную MCP-привязку.
- `pf.resolve --resource` возвращает состояние и reference выбранного ресурса
  из project-context snapshot. Единственный projector остался
  `command-history`, который rebuilds from durable events.

## Безопасность и границы

Проверка event ingress и read API сравнивает project Ledger presence с
запрошенным project. Cross-project event получает отказ. Daemon lifecycle,
`instance_id`, singleton, orphan protection, ready check и token IPC не
менялись по смыслу.

## Проверки

- `python -m py_compile ...` — PASS.
- `python tools/smoke_runtime_ledger_hooks_mcp.py` — PASS.
- `python tools/smoke_runtime_host_poc.py` — PASS.
- `python tools/smoke_long_lived_runtime.py` — PASS.
- `python tools/validate-process-forge-schemas.py --root .` — PASS.
- `python tools/validate-public-cleanliness.py --root .` — PASS.
- `python bin/pf.py project-context-check --project-root . --json` — fresh,
  policy `continue`.
- `git diff --check` — exit 0; only Windows line-ending notices.

## Честные границы доказательства

Focused smoke invokes the adapter executable with a Codex-shaped hook payload;
it does not claim a real `SessionStart`/`SessionEnd` delivery from this already
running Codex client. The project reference documents supported hook facts but
does not contain a deployable hook-config schema, and the user-level config has
no lifecycle binding. Therefore live self-hook proof is pending trusted Codex
hook installation/restart, not simulated as completed.

Automatic independent review is also pending: the prepared PF shell worker uses
the configured `manual` runtime driver and cannot be started automatically.

## Superseding final validation (2026-08-14)

The preceding two paragraphs describe the state before the Codex driver was
connected. They are superseded by
[live-validation.md](live-validation.md) and
[independent-review-waiver.md](independent-review-waiver.md).

The project-local hook configuration is now present in `.codex/hooks.json`.
A real `gpt-5.3-codex-spark` Codex CLI session produced successful
`SessionStart` and `PostToolUse` hook completions, delivered events through the
running Runtime, and left durable Ledger check-in, heartbeat, and checkout
records. The hook prints no normal stdout, so Codex accepts it as an advisory
lifecycle hook; debug JSON is restricted to the focused smoke via
`PF_CODEX_HOOK_DEBUG=1`.

The real PF `codex-exec` shell-worker driver completed the original independent
review and a remediation review. The initial review's two findings (MCP
cross-project root override and unauthenticated shutdown) were fixed, covered
by the focused smoke, and accepted by the remediation review.
