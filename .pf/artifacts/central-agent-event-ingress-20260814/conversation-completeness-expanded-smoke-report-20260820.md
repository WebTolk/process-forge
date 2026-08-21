# conversation-completeness-expanded-smoke-report-20260820

**Статус: PASS.**

## Что сделано

- Расширен `tools/smoke_conversation_completeness.py`; production source не изменялся.
- Smoke теперь создает временные PF fixture-проекты, run/task/assignment и manual worker-run state через публичные CLI-команды.
- Проверен реальный PF worker input path через `codex_exec_worker.prompt_payload()` + `capture_worker_input()`.
- Проверен collectible output path через `python tools/processforge.py worker-run collect --project-root <fixture> --task worker-task`.

## Покрытые сценарии

- Codex `UserPromptSubmit`: один user transcript message, replay возвращает тот же id, `chat.message.recorded` остается metadata-only.
- Forged PF worker provenance: envelope с валидной worker-сессией, но чужим `content_provenance`, отклоняется с `untrusted_conversation_provenance`.
- Missing session: PF worker envelope без `source_session_id` отклоняется с `missing_session`.
- Wrong attempt / foreign project binding: worker envelope с несуществующей попыткой и envelope, привязанный к другому onboarded project, отклоняются с `session_not_authorized`.
- Real PF worker input: durable prepared worker-run authorizes только ожидаемые `run_id`, `task_id`, `attempt`, `expected_report`; повторная доставка не создает второй transcript record.
- Recovery after transcript-before-event interruption: smoke удаляет один `chat.message.recorded` metadata event после записи transcript и повторно доставляет тот же worker input; transcript остается в одном экземпляре, metadata event восстанавливается.
- Concurrent duplicate delivery: два параллельных `runtime-host event` процесса доставляют один и тот же worker envelope; оба получают один `chat_message_id`, transcript и metadata event остаются дедуплицированными.
- Collectible expected report output: `worker-run collect` записывает ровно один assistant transcript message из exact expected-report file content и затем завершает task.
- Privacy invariant: project-visible events/outbox не содержат raw worker stdin, exact assistant report body, workspace-access markers, assignment-capsule markers или локальный private path marker; conversation events остаются metadata-only.

## Проверки

- `python tools/smoke_conversation_completeness.py` -> PASS (`PASS: conversation completeness smoke`).
- Focused `py_compile` для `tools/smoke_conversation_completeness.py`, `tools/processforge.py`, `tools/codex_exec_worker.py`, `tools/pf_runtime/host.py`, `tools/pf_runtime/codex_hooks.py` -> PASS.
- `git diff --check -- tools/smoke_conversation_completeness.py .pf/artifacts/central-agent-event-ingress-20260814/conversation-completeness-expanded-smoke-report-20260820.md` -> PASS.

## Ограничения и остаточные риски

- `tools/smoke_central_event_ingress.py` и полный `release-test` не запускались: эти файлы/широкий прогон не входят в разрешенный read scope этой worker assignment.
- После первого неудачного запуска Python `TemporaryDirectory` один локальный каталог `.tmp/pf-conversation-otb05bm0` остался недоступен для cleanup из-за Windows permission issue. Текущий smoke больше не использует `TemporaryDirectory`; новые fixture-каталоги создаются под `.tmp` явно и удаляются best-effort после успешного запуска.