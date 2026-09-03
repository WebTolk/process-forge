# conversation-completeness-final-rereview-2-20260820

**Итог: FAIL.**

Правка закрывает прежний blocker по произвольному `WorkerPromptPayloadSubmitted.content`: теперь worker-input должен иметь durable PF-owned contract, валидный `stdin_payload_hash`, совпадающий canonical summary и авторизованную worker-сессию. Но финальный критерий не выполнен полностью: idempotency остаётся слабой для логически того же worker input/output при изменённом `native_event_id`.

## Evidence

- `tools/codex_exec_worker.py:105-119`: launcher считает `stdin_payload_hash`, строит canonical summary и атомарно пишет `.pf/runtime/agent-runs/<run>/<task>/worker-input-contract.json`.
- `tools/pf_runtime/host.py:661-682`: Runtime заново считает hash из `raw_payload.stdin_payload`, требует совпадения с contract и canonical summary.
- `tools/pf_runtime/host.py:699-703`: `WorkerPromptPayloadSubmitted` теперь принимает только `pf_owned_safe_summary` и точное `worker_input_summary(...)`; прежний arbitrary safe summary должен быть отклонён.
- `tools/smoke_conversation_completeness.py:343-348`: negative smoke на `"forged safe system summary"` добавлен и ожидает `untrusted_conversation_provenance`.
- `tools/pf_runtime/host.py:770-785`: `message_id` строится от `receipt.raw_event_id` и content hash. Если тот же PF-owned worker input доставить с другим `native_event_id`, получится другой `raw_event_id` и другой `message_id`.
- `tools/smoke_conversation_completeness.py:372-387`: smoke фактически принимает `WorkerPromptPayloadSubmitted` с тем же `run_id/task_id/attempt`, тем же input hash/summary, но с неканоническим `native_event_id` из helper `worker_envelope(...)`, и проверяет только отсутствие дубля внутри parallel delivery этого нового event id. Он не проверяет запрет второго transcript-сообщения для уже записанного logical worker input.
- `tools/processforge.py:17928-17957` и `tools/pf_runtime/host.py:704-705,730-733`: output provenance по содержимому файла сохраняется, но тот же риск logical duplicate применим и к `WorkerExpectedReportCaptured`, потому что host не требует canonical `native_event_id`.

## Conclusion

Provenance forgeability по содержимому worker-input закрыта. Privacy boundary не ослаблена: project-visible event остаётся metadata-only через `append_chat_message()`, а полный input не попадает в derived conversation content.

Но требование “без ослабления idempotency” не доказано и по коду выглядит нарушенным: Runtime доверяет adapter-supplied `native_event_id` для derivation ключа сообщения и не связывает worker input/output conversation capture с canonical logical key `run_id/task_id/attempt/kind`. Для PASS нужно fail-closed требовать canonical worker native ids либо строить `message_id` для PF worker input/output от logical worker identity, а не от произвольного raw receipt id.

## Verification

Код не изменял. Smokes не запускал: задание read-only, текущая среда не разрешает запись временных project/runtime fixtures. Вывод основан на разрешённых source-файлах и двух предыдущих report-файлах из scope.