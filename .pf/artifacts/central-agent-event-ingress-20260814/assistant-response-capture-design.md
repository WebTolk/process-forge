# Assistant Response Capture Design

## Статус

Плановый дизайн без изменений исходного кода.

Главная корректировка к прежнему `chat-capture`: durable chat records должны поддерживать две роли - `user` и `assistant`, но записывать тело сообщения можно только там, где источник технически предоставляет это тело. Lifecycle events, статусы сессии, tool events, heartbeat, exit code и presence не являются содержимым ответа и не должны использоваться для реконструкции assistant message.

## Доказанная граница источников

### Codex hooks

В текущем PF adapter `tools/pf_runtime/codex_hooks.py` локально реализованы только:

- `SessionStart` -> `agent.session.started|resumed|compacted`;
- `SessionEnd` -> `agent.session.ended`;
- `PostToolUse` -> `agent.command.completed|agent.tool.completed`.

Официальный Codex hook contract по ранее зафиксированному аудиту шире и включает `UserPromptSubmit`. Это дает проектируемый путь для capture пользовательского prompt, если payload содержит реальное prompt-поле. При этом отдельный стабильный hook для per-message assistant response в найденном Codex contract не подтвержден. `transcript_path` нельзя считать стабильным API для чтения ответов.

Вывод: для generic Codex hooks поддерживаем только raw-first запись и provider-proven user prompt capture через `UserPromptSubmit`; generic Codex assistant response capture помечается как `unsupported`.

### PF-owned Codex worker

`tools/codex_exec_worker.py` является другим источником, не generic hook provider:

- PF сам формирует worker prompt через `prompt_payload(...)`;
- Codex CLI запускается через `codex exec ... -o <expected_report_path> -`;
- output delivery contract явно задает, что final response captured verbatim as expected report artifact;
- heartbeat и exit contract фиксируют состояние процесса, но не являются текстом ответа.

Вывод: для PF-launched Codex worker можно записывать assistant answer из PF-owned expected report/output file после завершения worker run. Это не доказывает generic Codex assistant hook capture и не должно смешиваться с ним в матрице возможностей.

## Минимальная provider-neutral raw-first граница

Расширить текущую модель `native envelope -> RawIngressKernel.ingest(...) -> optional derived effects`.

Envelope может опционально содержать:

```json
{
  "derived_chat_messages": [
    {
      "schema_version": 1,
      "message_role": "user|assistant|system|tool|subagent",
      "participant": {
        "id": "user|codex|worker:<task_id>",
        "type": "human|agent|subagent|tool",
        "role": "operator|assistant|worker"
      },
      "session_id": "<session>",
      "turn_id": "<provider turn id or derived raw id>",
      "content": "<provider-proven text>",
      "content_source": {
        "kind": "codex_hook|pf_codex_exec_output",
        "provider": "codex",
        "adapter": "codex-hooks|pf-codex-exec-worker",
        "native_event_type": "<event>",
        "content_provenance": "provider_payload|pf_owned_output_file"
      }
    }
  ]
}
```

Host/Core остаются provider-neutral:

- adapter извлекает provider-specific поля;
- Host проверяет project/session/access;
- Host вызывает общий transcript append;
- Core не знает, что такое Codex `UserPromptSubmit` или Codex CLI `-o`.

## Capture paths

### 1. Codex `UserPromptSubmit` -> user message

Добавить в `codex_hooks.native_envelope()` adapter-level mapping только для:

- `hook_event_name == "UserPromptSubmit"`;
- `cwd` присутствует;
- `session_id` присутствует;
- payload содержит непустой строковый `prompt`;
- роль контента доказана как user input.

Результат: raw record всегда сохраняется, transcript write выполняется только при валидном `derived_chat_messages[0]`.

Если `prompt` отсутствует или не строка: raw accepted, chat effect skipped, diagnostics: `chat_unsupported_or_missing_content`.

### 2. PF Codex worker output -> assistant message

Добавить отдельный PF-owned capture после завершения worker process и наличия expected report/output file:

- source kind: `pf_codex_exec_output`;
- message role: `assistant`;
- participant: текущий worker/agent id;
- content: содержимое expected report/output file;
- content_ref: путь к expected report artifact;
- статус worker должен подтверждать завершение, но сам по себе не является содержимым.

Не читать stdout/stderr как assistant body по умолчанию. Эти файлы являются process logs, а не стабильным semantic answer contract.

## Durable identity and retries

Базовая идентичность должна строиться от raw receipt или от PF-owned worker output fingerprint.

Для hook-derived chat:

```text
derived_key = deterministic_derived_key(
  raw_event_id,
  "chat_message",
  "processforge.chat-capture.<adapter>",
  "1",
  {
    "provider": "...",
    "adapter": "...",
    "native_event_type": "...",
    "source_session_id": "...",
    "message_role": "user|assistant"
  }
)
```

Для PF worker output:

```text
derived_key = sha256({
  "contract": "processforge.worker-output-chat-message.v1",
  "run_id": run_id,
  "task_id": task_id,
  "expected_report_path": expected_report_path,
  "expected_report_sha256": file_sha256,
  "message_role": "assistant"
})
```

Затем:

- `message_id = "msg_" + derived_key[:32]`;
- `event_id = "evt_" + sha256("chat.message.recorded:" + message_id)[:32]`.

`append_chat_message()` нужно сделать backward-compatible: optional `message_id` и `event_id`. При повторе существующего `message_id` transcript line не дублируется; `chat.message.recorded` дедуплицируется по deterministic `event_id`.

## Privacy and content semantics

- Raw payload остается private в workplace runtime raw storage.
- Transcript остается private в `.pf/runtime/chat/transcripts/<session-id>.ndjson`.
- `append_chat_message()` сохраняет существующую redaction/truncation логику.
- `chat.message.recorded` для automatic capture остается `metadata_only`: `content_hash`, `redaction`, `content_ref`, `content_mode`, без тела сообщения.
- Содержимое assistant expected report можно хранить в transcript, но публичные project artifacts не должны получать raw provider payload.
- Нет сетевой отправки и нового public API.

## Access checks

Перед transcript write:

- `source_project_ref` должен пройти `resolve_project()`;
- optional project/cwd внутри derived chat должен совпадать с raw envelope project;
- `session_id` обязателен;
- `ledger_session(session_id, workplace_root, core)` должен существовать и быть привязан к тому же `project_id`;
- для PF-owned worker output допускается привязка через run/task/session, но нельзя выводить process/stage/assignment из lifecycle metadata, если они не заданы durable assignment/run state.

При отказе доступа: raw accepted, chat denied, diagnostics recorded, no transcript write.

## Phased delivery

### Phase 1 - core-safe idempotent transcript append

- Расширить `append_chat_message()` optional `message_id/event_id`.
- Добавить duplicate lookup по `message_id`.
- Сохранить default UUID behavior для manual `chat-record`.
- Smoke: duplicate deterministic message не создает вторую transcript line.

### Phase 2 - Host derived chat sink

- Добавить private `_ingest_derived_chat_messages(...)` после raw ingest.
- Raw first, then derived event, then derived chat effects.
- Receipt возвращает `chat_message_ids` и diagnostics.
- Host не читает provider-specific поля.

### Phase 3 - Codex user prompt capture

- Добавить adapter mapping для `UserPromptSubmit`.
- Capture только provider-proven user prompt.
- Missing prompt -> raw only.
- Явно зафиксировать generic Codex assistant response as unsupported.

### Phase 4 - PF Codex worker assistant output capture

- После completed worker run и существующего expected report создать assistant transcript message.
- Источник: `pf_codex_exec_output`.
- Использовать deterministic identity от run/task/output hash.
- Не использовать stdout/stderr как semantic answer.

### Phase 5 - tests and matrix update

- Smoke: Codex user prompt -> raw + user transcript + metadata-only event.
- Smoke: PF Codex worker expected report -> assistant transcript + metadata-only event.
- Smoke: repeated delivery does not duplicate transcript.
- Smoke: generic Codex lifecycle events do not create assistant messages.
- Update capability matrix: `Codex hooks user prompt: supported after slice`; `Codex hooks assistant answer: unsupported`; `PF Codex worker final answer: supported via owned output`.

## Acceptance boundary

Delivery is acceptable only if durable records can show:

- user prompt where provider/PF supplies actual prompt text;
- assistant answer where PF owns the output file or provider contract supplies actual assistant text;
- no assistant answer fabricated from `SessionEnd`, `PostToolUse`, exit code, heartbeat, task status, or lifecycle metadata.
