# Узкий тестовый контракт: полнота conversation capture

**Статус:** ready_for_review
**Назначение:** исполнимый acceptance-contract для bounded conversation-capture slice; не является подтверждением её реализации.

## Smoke и fixtures

- Новый `tools/smoke_conversation_completeness.py`, зарегистрированный в `release-test`; существующий `tools/smoke_central_event_ingress.py` сохраняет raw-first/replay coverage.
- Временный workplace и два onboarded generic projects (`first`, `second`); один PF run/task/assignment с collectible expected report, PF worker session и Codex session.
- Фиксированные UTF-8 payload/report, attempt, native ids и конкурентный барьер для двух delivery одного envelope. До/после каждого case читаются private raw shards, transcript NDJSON и project events/outbox.

## Обязательные сценарии

| ID | Действие | Обязательные assertions |
| --- | --- | --- |
| `input.raw_first` | Worker строит именованный exact UTF-8 `payload_text`, вычисляет hash, отправляет `WorkerPromptPayloadSubmitted`, затем запускает CLI. | Raw хранит exact bytes/text и тот же `stdin_payload_hash`; stdin равен сохранённому payload; один system message с safe summary; raw receipt accepted и возвращает один deterministic `chat_message_id`. При rejected/quarantined receipt CLI не запускается. |
| `input.privacy` | В summary/source подаются capsule body, full payload, workspace-access ref/content, raw location и абсолютный path. | Каждый unsafe вариант отклонён conversation sink'ом: raw receipt остаётся, transcript/event не добавлены, есть структурированная denial diagnostic. Успешные transcript, `chat.message.recorded`, events, outbox и expected report не содержат marker raw payload/secret или запрещённые значения. |
| `output.collectible` | Выполняется collect с существующим required output и exact expected report. | До `command_task_complete` создан ровно один assistant message из exact expected-report content; `WorkerExpectedReportCaptured` raw содержит hash/content; output sink возвращает ровно один message id; затем task completed и `worker.run.collected`. |
| `output.fail_closed` | Collect вызывается при missing/non-collectible report, при stdout/stderr-only output и при sink, возвращающем 0 либо >1 id. | Нет assistant message; `command_task_complete` и `worker.run.collected` не вызваны. stdout, stderr, exit/lifecycle/heartbeat/task-status и hook telemetry никогда не становятся assistant content. |
| `host.authorization` | Conversation envelope имеет missing/unrouted PF session, foreign-project binding или `source_project_ref` второго проекта. | Raw receipt сохранён; `chat_message_ids == []`; transcript и metadata event отсутствуют; diagnosis указывает denial reason. Valid PF worker session авторизуется по durable run/task/assignment и project match. |
| `host.ordering` | Envelope содержит valid conversation и `derived_event`, затем variant с invalid conversation. | При valid: raw -> conversation append -> metadata-only `chat.message.recorded` -> telemetry; telemetry может ссылаться только на ids/hashes. При invalid: raw + denial, без conversation; telemetry не превращается в content. |
| `idempotency.recovery` | Input и output доставляются повторно; затем имитируется interruption после accepted raw и до derived effect. | Повтор возвращает те же message/event ids, восстанавливает отсутствующий effect, но не добавляет вторую transcript NDJSON строку, второй `chat.message.recorded`, telemetry event или raw record. |
| `idempotency.concurrent` | Два одновременных delivery одинакового valid envelope стартуют на барьере. | Atomic transcript/event dedupe: один transcript record и один deterministic metadata event, оба callers получают тот же message id, нет corrupted NDJSON. |
| `codex.user_prompt` | Valid textual `UserPromptSubmit`, затем missing и non-string prompt; отдельно `SessionStart`, `SessionEnd`, `PostToolUse`, `Stop`. | Valid prompt: raw + ровно один user message + metadata-only event. Missing/non-string: raw-only, empty ids. Остальные hooks: raw/telemetry только, без conversation message любого role. |

## Инварианты содержания и идентичности

- Automatic message id и `chat.message.recorded` event id детерминированы из raw event, adapter/version, session/turn/role/sequence и SHA-256 stored content; manual UUID behavior остаётся вне этого smoke.
- Input role — только `system`, Codex `UserPromptSubmit` — только `user`, collectible expected report — только `assistant`; поддерживаются лишь документированные provenance/kind.
- Automatic `chat.message.recorded` metadata-only: допустимы id, participant, role, content hash/redaction, relative transcript ref; body запрещён.
- Safe summary допускает только stable ids, hashes и relative expected-report ref. Абсолютные пути, capsule/workspace-access/raw refs и их содержимое запрещены в content и source.

## Финальные gates

1. Новый smoke и `tools/smoke_central_event_ingress.py` PASS; новый smoke включён в `release-test`.
2. `python tools/processforge.py events-validate --project-root <fixture-project>` PASS для всех fixture events.
3. `python -m py_compile tools/processforge.py tools/codex_exec_worker.py tools/pf_runtime/host.py tools/pf_runtime/codex_hooks.py` PASS.
4. Проверка marker-строк подтверждает отсутствие raw payload/secret и запрещённых источников во всех project-visible outputs.

## Запрещённые источники assistant content

Только exact collectible expected report может породить assistant message. Строго запрещены: stdout, stderr, Codex CLI diagnostics, lifecycle/hooks (`SessionStart`, `SessionEnd`, `PostToolUse`, `Stop`), heartbeat, exit contract, task/run status, telemetry `derived_event`, outbox и raw ingress.
