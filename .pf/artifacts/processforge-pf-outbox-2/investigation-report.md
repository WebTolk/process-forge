# Investigation Report: Аудит предыдущей работы и статус хуков PF outbox

## 1. Предыдущая работа по hooks/audit

### Активные/завершённые Work
| Run / Assignment | Статус | Комментарий |
|---|---|---|
| `garage-configure-kimi-code-host-hooks-...` / `configure-kimi-code-host-hooks-for-processforge-project-and-document-set` | in_progress (orchestration) | Создан `kimi_hooks.py`, `kimi_adapters.py`, обновлён host config; live test отложен из-за отсутствия Ledger-bound session. |
| `garage-e2e-smoke-unit-runtime-drivers-agent-entry-adapters-hook-delivery` | in_progress (orchestration) | Smoke/unit проверка runtime drivers, adapters, hooks, events; evidence записаны. |
| `garage-full-current-pf-audit-static-executor-20261014-independently-insp` | failed | Worker runtime завершился `unknown_exit: process exited without durable exit contract`. |
| `pf-forge-hooks-followup-20261020` | cancelled | Planning-only handoff для будущей регистрации hook-adapters. |

### Ключевые артефакты
- `.pf/artifacts/kimi-hooks-setup-20261021/setup-report.md` — установка Kimi Code host hooks.
- `.pf/hooks.yaml` — текущая проектная hook-конфигурация.

## 2. Конфигурация хуков

Файл `.pf/hooks.yaml`:
- `mode: outbox`
- `network_send_enabled: false`
- Включён target `wtaicc-outbox` (type: `outbox`, path: `.pf/runtime/hooks/outbox/wtaicc`, event_types: `*`).
- Цели `local-audit` (command) и `wtaicc-webhook-future` (webhook) отключены.

Workplace: `D:\.agents\processforge-workplace\workplace.yaml` — `default_project_mode: organized` (Forge). Проект наследует этот режим.

## 3. Фактическое состояние outbox

- `.pf/runtime/hooks/outbox/wtaicc/` содержит **140 457** JSON-файлов (проверено через `python glob`).
- Накоплены события от `processforge.cli` и, в меньшей степени, `processforge.supervisor`.
- Присутствуют события `process.stage.completed`, `process.stage.transitioned`, `process.stage.started` для текущей Work `processforge-pf-outbox-2` (обнаружены 12 релевантных файлов среди последних 10 000 записей).
- События `supervisor.tick.completed` доминируют в выборке, что указывает на периодическую работу execution-inspector/supervisor.

## 4. Путь доставки хуков (код)

1. `ProcessEventRecorder.admit_process_event()` — записывает событие в `.pf/runtime/events/events.sqlite3` и, если `dispatch=True` и target выбран, помещает в `pending_dispatch`.
2. `RuntimeHookDispatcher.dispatch_hooks()` — для enabled outbox-target записывает payload в `.pf/runtime/hooks/outbox/...` и результат в `.pf/runtime/hooks/results/...`.
3. `WorkTransitionCommitService.commit()` — при переходе стадии вызывает `WorkEventPublisher.publish()` → `_emit()` → `ProcessEventRecorder.emit_process_event()`.

Таким образом, **автоматическая запись хуков в outbox при Work transitions работает штатно**.

## 5. Kimi Code host hooks

- `tools/pf_runtime/kimi_hooks.py` — адаптер для Kimi Code lifecycle payload'ов.
- `tools/pf_runtime/kimi_adapters.py` — `KimiHooksPolicy`, зарегистрирована в `tools/pf_runtime/builtin_provider_adapters.py`.
- Host config `C:\Users\musst\.kimi-code\config.toml` содержит `[[hooks]]` для всех lifecycle events, вызывающие `python D:/dev/process-forge/tools/pf_runtime/kimi_hooks.py`.

Ограничение из setup-report: end-to-end проверка с реальной session не выполнялась; `pf.project_initialization.repair` отказал из-за `session: absent`.

## 6. Проблемы и находки

1. **Предыдущий полный аудит (`full-current-pf-audit-static-executor`) упал** — причина не установлена, требуется отдельная Work для диагностики worker-runtime `unknown_exit`.
2. **Отсутствие Ledger-bound host session** блокирует live-проверку Kimi Code hook delivery. Статус `session: absent` в текущем контексте.
3. **Outbox накапливает большой объём** (140k+ файлов). Политика ротации/очистки не выявлена в `.pf/hooks.yaml` — это потенциальный риск дискового пространства.

## 7. Вывод

- Хуки PF **записываются автоматически** в outbox при событиях процесса (transitions) и supervisor ticks.
- Host-регистрация Kimi Code hooks настроена, но не подтверждена live.
- Для полного соответствия ожиданию «PF должен записывать хуки автоматически» достаточно текущей конфигурации; live-проверка host hooks требует session.
