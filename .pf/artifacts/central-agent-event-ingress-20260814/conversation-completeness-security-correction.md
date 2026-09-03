# Conversation Completeness Security Correction

## Вердикт

`PASS` для плановой коррекции. Исходный код не изменялся.

Коррекция закрывает блокирующие замечания security review: полный PF-owned launch payload больше не попадает в project transcript; authoritative capture переносится на реальную границу генерации stdin payload; transcript получает только безопасную system-summary запись; output capture привязан к completed/collectible boundary.

## Подтвержденная причина блокировки

Текущий `prompt_payload()` формирует полный stdin для `codex exec` из worker prompt, output contract, capsule body и ссылки на workplace access, а затем передает его в `subprocess.run(..., input=...)` внутри `tools/codex_exec_worker.py`.

Следовательно, capture в `worker-run start` вокруг `Popen` в `tools/processforge.py` не является canonical source: там запускается wrapper, а не сам `codex exec` stdin payload.

## Исправленная архитектурная граница

Authoritative PF-owned input capture должен выполняться в `tools/codex_exec_worker.py` непосредственно после построения `payload_text = prompt_payload(...)` и непосредственно перед `subprocess.run(...)`.

Правило:

- full `payload_text` сохраняется только через central raw ingress в workplace-private raw storage;
- project transcript не получает `payload_text`;
- transcript получает только безопасное system message summary;
- если raw input capture не выполнен, worker subprocess не запускается.

## Central Ingress Handoff

`codex_exec_worker.py` должен передать native envelope в `pf_runtime.host.ingest_event(...)` до запуска Codex CLI.

Envelope для input:

```json
{
  "schema_version": 1,
  "provider": "processforge",
  "adapter": "pf-codex-exec-worker",
  "native_event_type": "WorkerPromptPayloadSubmitted",
  "native_event_id": "worker-input:<run_id>:<task_id>:attempt:<attempt>",
  "native_id_scope": "project",
  "native_event_id_stable": true,
  "source_session_id": "pf-worker:<run_id>:<task_id>:attempt:<attempt>",
  "source_project_ref": "<resolved project root>",
  "payload_version": "1",
  "raw_payload": {
    "run_id": "<run_id>",
    "task_id": "<task_id>",
    "attempt": "<attempt>",
    "stdin_payload": "<exact prompt_payload text>",
    "stdin_payload_hash": "<sha256>",
    "output_contract": "expected_report"
  },
  "derived_conversation_messages": [
    {
      "message_role": "system",
      "participant": {
        "id": "processforge-runtime",
        "type": "system",
        "role": "worker_launcher"
      },
      "session_id": "pf-worker:<run_id>:<task_id>:attempt:<attempt>",
      "turn_id": "worker-turn:<run_id>:<task_id>:attempt:<attempt>",
      "content": "ProcessForge launched a Codex worker for run `<run_id>`, task `<task_id>`, attempt `<attempt>`. Full PF-owned launch input is stored in private raw ingress. stdin_payload_hash=`<sha256>`. expected_report=`<relative expected report artifact>`.",
      "content_source": {
        "kind": "pf_codex_exec_input",
        "provider": "processforge",
        "adapter": "pf-codex-exec-worker",
        "native_event_type": "WorkerPromptPayloadSubmitted",
        "content_provenance": "pf_owned_safe_summary"
      },
      "delivery": {
        "state": "complete",
        "sequence": 0,
        "final": true
      }
    }
  ]
}
```

Запрещено включать в transcript summary:

- capsule body;
- full launch payload;
- workplace access reference;
- contents of workplace access;
- absolute paths;
- raw ingress filesystem location.

Допустимы только stable ids, relative expected report artifact, `raw_event_id`, `stdin_payload_hash`, `content_hash`.

## Output Capture Boundary

PF-owned assistant output capture должен выполняться в `command_worker_run_collect()` после всех проверок collectible state и наличия expected report, но до `command_task_complete(...)` и `worker.run.collected`.

Envelope для output:

```json
{
  "schema_version": 1,
  "provider": "processforge",
  "adapter": "pf-codex-exec-worker",
  "native_event_type": "WorkerExpectedReportCaptured",
  "native_event_id": "worker-output:<run_id>:<task_id>:attempt:<attempt>:<report_hash>",
  "native_id_scope": "project",
  "native_event_id_stable": true,
  "source_session_id": "pf-worker:<run_id>:<task_id>:attempt:<attempt>",
  "source_project_ref": "<resolved project root>",
  "payload_version": "1",
  "raw_payload": {
    "run_id": "<run_id>",
    "task_id": "<task_id>",
    "attempt": "<attempt>",
    "expected_report": "<relative expected report artifact>",
    "report_content": "<exact expected report file content>",
    "report_hash": "<sha256>"
  },
  "derived_conversation_messages": [
    {
      "message_role": "assistant",
      "participant": {
        "id": "<worker id>",
        "type": "agent",
        "role": "worker"
      },
      "session_id": "pf-worker:<run_id>:<task_id>:attempt:<attempt>",
      "turn_id": "worker-turn:<run_id>:<task_id>:attempt:<attempt>",
      "parent_message_id": "<input message id>",
      "content": "<expected report file content>",
      "content_source": {
        "kind": "pf_codex_exec_output",
        "provider": "processforge",
        "adapter": "pf-codex-exec-worker",
        "native_event_type": "WorkerExpectedReportCaptured",
        "content_provenance": "pf_owned_output_file"
      },
      "delivery": {
        "state": "complete",
        "sequence": 1,
        "final": true
      }
    }
  ]
}
```

Если output capture не возвращает ровно один `chat_message_id`, collect должен завершиться ошибкой и не должен переводить task в completed.

## Conversation Sink Contract

`host.ingest_event()` должен после успешного `RawIngressKernel.ingest(...)` обрабатывать `derived_conversation_messages[]` отдельным sink, независимо от telemetry `derived_event`.

Порядок:

1. Persist raw envelope.
2. If raw receipt is rejected/quarantined: return receipt, no transcript write.
3. Validate `derived_conversation_messages[]`.
4. Append deterministic transcript messages.
5. Return `chat_message_ids`.
6. Route `derived_event`, if present, after transcript write so telemetry may reference message ids without message body.

Conversation sink must deny transcript write but keep raw receipt when:

- session is missing or not authorized;
- session is bound to another project;
- content is missing or non-string;
- message role/provenance is unsupported;
- source project mismatches envelope project.

PF-owned worker sessions are authorized by durable run/task/assignment under the resolved project. Generic provider sessions require Agent Ledger routing.

## Message Identity

`append_chat_message()` needs optional deterministic ids while preserving current UUID behavior for manual `chat-record`.

For each derived message:

```text
content_hash = sha256(stored transcript content)

derived_key = deterministic_derived_key(
  raw_event_id,
  "conversation_message",
  "processforge.conversation-capture.<adapter>",
  "1",
  {
    "session_id": session_id,
    "turn_id": turn_id,
    "message_role": message_role,
    "delivery_sequence": delivery.sequence,
    "content_hash": content_hash
  }
)

message_id = "msg_" + derived_key[:32]
event_id = "evt_" + sha256("chat.message.recorded:" + message_id)[:32]
```

Duplicate handling:

- if `message_id` already exists in transcript, do not append a second line;
- return the existing `message_id`;
- `append_process_event()` deduplicates `chat.message.recorded` by deterministic `event_id`.

## Privacy Rules

- Raw provider/PF payload remains only in workplace-private raw ingress.
- Transcript body remains only in private chat transcript storage.
- Automatic `chat.message.recorded` is metadata-only.
- `chat.message.recorded` may include `message_id`, participant, role, `content_hash`, redaction state, relative transcript ref, and `content_mode=metadata_only`.
- Automatic event payload must not include message body.
- Public artifacts, assignment capsules, reports, hook outbox payloads, and process events must not receive raw provider payload, capsule body, workplace access content, workplace access references, or absolute private paths.
- No network send is introduced.

## Focused Acceptance

1. Worker input capture occurs inside `codex_exec_worker.py` immediately before `subprocess.run(...)`.
2. Exact PF-owned stdin payload is present only in raw ingress private storage.
3. Input transcript record is `system`, not `user`.
4. Input transcript content is safe summary only.
5. Completed worker collect creates one assistant transcript record from expected report content.
6. Re-running input/output capture does not duplicate transcript lines.
7. Re-running capture does not duplicate `chat.message.recorded`.
8. `SessionStart`, `SessionEnd`, `PostToolUse`, `Stop`, heartbeat, exit contract, task status, stdout, and stderr never create assistant messages.
9. Valid Codex `UserPromptSubmit` creates raw record, user transcript record, and metadata-only `chat.message.recorded`.
10. Missing/non-string prompt creates raw record only and returns empty `chat_message_ids`.
11. Session bound to another project creates raw record only, denies transcript write, and reports diagnostics.
12. Generated events pass `events-validate`.
13. Transcript validation rejects absolute paths and workplace access references in automatic message content/source.
