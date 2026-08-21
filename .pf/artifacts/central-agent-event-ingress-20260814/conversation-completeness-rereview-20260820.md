# Повторный независимый review: полнота conversation capture

**Итог: FAIL.** Целевой smoke проходит, а replay metadata-event исправлен, но worker-ветка ещё не обеспечивает строгую provenance/session boundary.

## Проверено

- **Allowlist для Codex user prompt: PASS.** Разрешена только точная комбинация `codex/codex-hooks/UserPromptSubmit/user/codex_hook/provider_payload`; текст обязан совпадать с `raw_payload.prompt`, а сессия сверяется с Agent Ledger.
- **Replay metadata-event: PASS.** В `append_chat_message()` при уже существующем `message_id` и переданном `event_id` заново вызывается `emit_process_event("chat.message.recorded", ...)`. После сбоя между записью transcript и metadata-event повторная доставка может восстановить отсутствующий event без второй строки transcript.
- **Целевой smoke: PASS.** `python tools/smoke_conversation_completeness.py` завершился успешно.

## Блокер

**Worker provenance/session: FAIL.** Для `processforge/pf-codex-exec-worker` проверка `source_session_id` сопоставляет только строковый шаблон с полями, полностью пришедшими из `raw_payload`. `_worker_session_authorized()` дополнительно сверяет лишь существование задачи и её `run_id`; она не подтверждает активную/ожидаемую попытку и не связывает `attempt`, `source_session_id`, `expected_report` и `report_content` с durable PF-owned worker state/report-файлом. Поэтому локально поданный envelope с известными `run_id`/`task_id`, произвольным `attempt` и поддельной декларацией `pf_owned_output_file` пройдёт allowlist и запишет произвольный assistant/system content.

Необходима fail-closed проверка ожидаемой worker attempt и PF-owned report path/content против durable worker state до capture; затем smoke должен покрыть forged/missing/foreign session и forged worker provenance.
