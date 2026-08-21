# conversation-completeness-final-rereview-20260820

**Итог: FAIL.**

Финальная правка закрыла часть прежнего блокера по worker-output: `WorkerExpectedReportCaptured` теперь сверяет `attempt` с durable worker state, `expected_report` с assignment, а `report_content` с фактическим PF-owned файлом отчёта. Но строгая provenance-граница для worker-input всё ещё неполная.

## Проверено

- `tools/pf_runtime/host.py:675-698`: `_worker_session_authorized()` проверяет `run_id/task_id`, совпадение `attempt` с `status.json`, `expected_report`, а для `WorkerExpectedReportCaptured` ещё и точное совпадение `report_content` с файлом отчёта.
- `tools/processforge.py:17923-17958`: `worker-run collect` читает expected report из файла и отправляет его как `pf_owned_output_file`; это достаточно строго для collectible assistant report.
- `tools/processforge.py:10561-10584`: повторная доставка существующего `message_id` может восстановить metadata-event без второй строки transcript.
- `tools/processforge.py:17313-17335`, `17748-17755`, `17768-17775`, `17876-17880`: worker lifecycle операции защищены lock и перед статусом/сбором проходят reconciliation.
- `tools/processforge.py:17631-17643`: durable `exit.json` переводит running state в terminal state.
- `tools/smoke_conversation_completeness.py`: smoke покрывает Codex prompt capture, replay, wrong attempt, foreign project, forged provenance, parallel duplicate delivery, collectible report, metadata-only events.
- `tools/smoke_worker_run_shell.py`: smoke покрывает duplicate start, prepare while running, direct driver-ref recovery и durable exit reconciliation.

## Блокер

**Worker input provenance остаётся forgeable.**

В `tools/pf_runtime/host.py:668-669` для `WorkerPromptPayloadSubmitted` allowlist проверяет только `(role, kind, provenance) == ("system", "pf_codex_exec_input", "pf_owned_safe_summary")`. В отличие от output-ветки на `tools/pf_runtime/host.py:670-671`, она не сверяет `item.content` с каноническим PF-generated summary и не связывает его с `raw_payload.stdin_payload_hash`.

Следствие: локально поданный native envelope с валидными `run_id`, `task_id`, текущим `attempt`, корректным `expected_report` и allowlisted `content_source` может записать произвольный safe system-message в transcript worker-сессии. Проверка `tools/pf_runtime/host.py:732-733` отсекает секреты и абсолютные пути, но не доказывает PF-owned provenance самого input content.

## Условия для PASS

- Для `WorkerPromptPayloadSubmitted` нужно fail-closed сверять content с канонической строкой, построенной из `run_id`, `task_id`, `attempt`, `stdin_payload_hash`, `expected_report`, либо другим durable PF-owned input digest contract.
- Smoke должен добавить negative case: correct provenance + correct session/attempt + arbitrary safe input content должен получить `untrusted_conversation_provenance` или отдельный denied reason.
- После этого текущие позитивные проверки по collectible report, replay/idempotency и durable lifecycle reconciliation выглядят достаточными.

## Верификация

Код не изменял. Smokes в этом worker не запускались: задание передано как read-only report capture, а доступная среда не разрешает запись временных project/runtime fixture-ов. Вывод основан на разрешённых source-файлах и предыдущих отчётах в scope.