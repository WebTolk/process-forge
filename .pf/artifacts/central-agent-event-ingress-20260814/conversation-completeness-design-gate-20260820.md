# Independent pre-implementation design gate: conversation completeness

**Assignment:** `central-ingress-conversation-completeness-design-gate-20260820`
**Verdict:** **PASS** — это PASS проектного решения, не утверждение о наличии реализации.

`conversation-completeness-security-correction.md` задаёт достаточную безопасную
границу для всех пяти условий pause-checkpoint. Реализация должна в точности
сохранить указанный ниже порядок; появление assistant-сообщения из stdout, stderr
или lifecycle/telemetry означает FAIL.

| Gate | Verdict | Сверка с фактической границей |
| --- | --- | --- |
| 1. Exact payload только в private raw | **PASS** | Реальный payload строится в `tools/codex_exec_worker.py:56-76`, а фактический stdin передаётся в `:150-154`. Поэтому именованный `payload_text` и его SHA-256 должны быть созданы один раз непосредственно перед этим вызовом, переданы в `host.ingest_event()` как `WorkerPromptPayloadSubmitted`, и тот же объект должен быть закодирован для stdin. `RawIngressKernel` пишет raw в workplace-root (`tools/pf_runtime/raw_ingress_kernel.py:195-239,308-324`). При rejected/quarantined receipt запуск запрещён; accepted duplicate допустим и не должен создавать новую запись transcript. |
| 2. В transcript только безопасная system-summary | **PASS** | Сейчас Host после raw обрабатывает лишь `derived_event` (`tools/pf_runtime/host.py:669-688`), поэтому correction правильно требует отдельный `derived_conversation_messages[]` sink. В summary разрешены только stable ids, hash и относительный report ref; capsule, workspace-access, raw-location и абсолютные пути не передаются. Sink обязан отклонять небезопасные content/source, но сохранить raw receipt с диагностикой. |
| 3. Canonical pre-exec capture и общий digest | **PASS** | Единственная canonical граница — `codex_exec_worker.py:150-152`, не внешний `Popen` в `tools/processforge.py:17750-17759`. Один UTF-8 `payload_text` и один `stdin_payload_hash` связывают raw envelope и исполняемый stdin; failure capture закрывает запуск. |
| 4. Assistant только после collectible expected report | **PASS** | `command_worker_run_collect()` сначала проверяет collectible state и required outputs/report (`tools/processforge.py:17830-17872`), затем сейчас завершает задачу (`:17873-17876`). Correction помещает `WorkerExpectedReportCaptured` строго между этими точками: читается только expected report, успешный sink обязан вернуть ровно один message id, иначе `command_task_complete()` и `worker.run.collected` не вызываются. Hooks уже ограничены lifecycle/tool facts (`tools/pf_runtime/codex_hooks.py:21-70`); их нельзя расширять до assistant content. |
| 5. Независимые идемпотентные conversation и telemetry | **PASS** | Существующий Host отделяет raw от `derived_event`; conversation должен быть вторым независимым sink до telemetry. Имеется готовый primitive deterministic derived key (`raw_ingress_kernel.py:86-104`), а `append_chat_message()` сейчас генерирует UUID и всегда append (`processforge.py:10526-10599`), поэтому его расширение deterministic `message_id` и deterministic event id необходимо. Идемпотентная проверка+append должна быть защищена одним transcript/event lock: простого чтения существующих строк недостаточно при параллельном delivery. Дубликат raw не прекращает попытку восстановить отсутствующий derived effect; он лишь не должен добавлять вторую строку/event. |

## Обязательный ограниченный code scope

- `tools/codex_exec_worker.py`: построить один payload, private raw input envelope и fail-closed submit до `subprocess.run`; не выводить raw payload, receipt location либо workspace-access в stdout/stderr/heartbeat.
- `tools/pf_runtime/host.py`: валидировать и независимо маршрутизировать `derived_conversation_messages[]` после accepted raw, включая PF worker-session authorization по run/task/assignment, project match и structured diagnostics при transcript denial. Telemetry остаётся в существующем `derived_event` пути и идёт после conversation.
- `tools/processforge.py`: поддержать deterministic/idempotent automatic append и metadata-only deterministic `chat.message.recorded`; добавить atomic transcript/event dedupe. В collect прочесть exact expected report и ingest output до task completion; при нуле или более одного message id оставить task незавершённой.
- `tools/pf_runtime/codex_hooks.py`: только для документированного `UserPromptSubmit` сформировать user conversation envelope при валидном текстовом prompt; `SessionStart`, `SessionEnd`, `PostToolUse`, `Stop` и прочая telemetry не создают conversation messages. Missing/non-string prompt остаётся raw-only.

## Обязательный узкий test contract

1. Input: exact UTF-8 payload/hash, raw-first submit до exec, и отсутствие exec при rejected capture.
2. Privacy: transcript summary и automatic source отвергают capsule/workspace-access/raw path/absolute path; raw payload не появляется в process events, outbox, expected report или telemetry.
3. Output: только collectible expected report порождает ровно одну assistant-запись до task-complete; stdout/stderr и hook/lifecycle facts не порождают её; sink failure не завершает task.
4. Authorization: missing/unrouted или cross-project session дают raw receipt без transcript и с диагностикой.
5. Idempotency/recovery: повтор input/output и повтор после raw-accepted/derived-interrupted возвращают те же ids без второй NDJSON строки и без второго `chat.message.recorded`; включить конкурентный append case.
6. Codex hook: valid `UserPromptSubmit` даёт raw + одну user-запись + metadata-only event; missing/non-string prompt — только raw. Проверить `events-validate` для всех generated events.

Наличие этих изменений в исходниках сейчас не проверялось как условие PASS: assignment требует оценить выполнимость безопасного плана до implementation. Текущий source ожидаемо не содержит conversation sink и не должен трактоваться как отклонение design gate.
