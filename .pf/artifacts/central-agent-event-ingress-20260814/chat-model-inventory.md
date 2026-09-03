# chat-model-inventory

## Модель хранения чата (факт)

- **Формат записи**: приватные NDJSON-транскрипты, по одному файлу на сессию.
- **Путь хранения**: `.pf/runtime/chat/transcripts/<session-id>.ndjson` (через `chat_transcript_path`).
- **Формат строки**: объект по `schemas/chat-message.schema.json`, каждая строка — отдельное сообщение.
- **Основные обязательные поля сообщения**:
  - `schema_version`, `message_id`, `session_id`, `turn_id`, `timestamp`
  - `participant` (`id`, `type`, `role`)
  - `message` (`role`, `content_type`, `content`, `content_hash`, `redaction`)
  - `source`, `process`, `assignment`
- **Поля-ограничения**:
  - `message_id`: `msg_<hex>` (`^msg_[a-z0-9]+$`)
  - `schema_version: 1`
  - `participant.type` ∈ `{human,agent,subagent,tool}`
  - `message.role` ∈ `{user,assistant,system,tool,subagent}`
  - `message.content_hash` = `sha256:<hex64>`
  - `message.redaction` ∈ `{none,redacted,truncated,redacted_truncated}`
- **Пограничные поля записи**:
  - `participant_type` выводится из `participant_id`, если не передан:
    `operator/user → human`, `subagent* → subagent`, иначе `agent`.
  - `parent_message_id` хранится как опциональное поле.
  - `source.kind` хранится как `source_kind` из команды (по умолчанию `manual_capture`).
  - `process.id`, `process.stage_id`, `assignment.id` — опциональные связи.

## Семантика `chat.message.recorded` и `chat-record`

- `chat-record` вызывает `append_chat_message(...)` и **всегда** пишет один объект в транскрипт, затем эмитит событие `chat.message.recorded`.
- Транскрипт и событие используют один и тот же `message_id`:
  - событие: `session_id`, `message_id`, `participant`, `message` с `content_hash`, `redaction`, `content_ref`.
- `content_ref` в событии: `path + line + message_id`.
- По умолчанию событие публикует только метаданные:
  - `message.content_mode = metadata_only`
  - `message.content` в событии отсутствует.
- Полная (редактированная/редакционированная) строка в событие попадает только при `--include-content` (появляется как `message.content`, `content_mode = full`/`redacted`).

## Корреляция и границы сессии

- Границы транскрипта жёстко привязаны к `session_id` (имя файла транскрипта), отдельный transcript на сессию.
- Корреляция событий `chat.message.recorded`: `correlation_id = session_id`.
- `event_id`/`message_id` генерируются в `processforge_event`/`append_chat_message` при записи.
- Валидация (`events-validate`) проверяет только структурную корректность NDJSON и схемы `event`/чат-сообщений; не проверяет бизнес-линки между сессией/процессом/присваиванием семантически.
- `chat-export` добавляет отдельное событие типа `session.message.recorded` с метаданными экспорта (`message_count`, `target`) и пишет отдельный payload в outbox (не заменяя `chat.message.recorded`).

## Hook/схемная связка для чата

- `dispatch_hooks` пишет payload в `.pf/runtime/hooks/outbox/` для выбранных hook-таргетов.
- Для `wtaicc` payload выглядит как: `event` + `chat` (`included`, `mode`, `messages`) через `wtaicc_outbox_payload`.
- `chat-export` без `--include-content` отдаёт `chat.mode = metadata_only`; с флагом — `full` (передаёт редактированный контент, уже подвергнутый redaction).
- Файл `hooks.yaml` по умолчанию для `wtaicc-webhook-future` слушает `chat.message.recorded`, но не `session.message.recorded`.
- `session.message.recorded` используется в `chat-export` как служебная отметка экспорта и имеет `privacy: sanitized`.

---

# event-schema-reconciliation

## Карта применяемых схем и фактических реализаций

### 1) `schemas/event-envelope.schema.json` (актуальная структура envelope)
- Требует: `schema_version,event_id,event_type,source,subject,time,correlation_id,project,process,assignment,actor,data`.
- Тип `event_id` жёстко `^evt_[a-z0-9]+$`.
- `actor` обязателен с `type/id/role`.

### 2) `schemas/process-event.schema.json` (перечень типов)
- Содержит подмножество/исторический enum для `event_type`.
- **Не требует** `source/actor/assignment/process` и др. (хуже, чем envelope).
- `event_type` у этого schema не покрывает ряд реально испускаемых типов (см. ниже).

### 3) Кодовая истина для типов (`REQUIRED_PROCESSFORGE_EVENT_TYPES`)
- Содержит расширенный и более широкий список event_type (включая `run.*`, `task.*`, `package.*`, `workplace.*`, `template.*`, `knowledge.*`, `platform.*`, `authoring_*` и др.).
- `hooks-dispatch` валидирует `event_type` именно по этому списку.

### 4) `schemas/chat-message.schema.json` vs. `append_chat_message`
- Поля транскрипта соответствуют требованиям схемы, включая обязательный `content`, `content_type`, `content_hash`.
- Нормальная реализация всегда пишет `content` в файл-транскрипт, но **из коробки скрывает его из `chat.message.recorded`**.

### 5) `schemas/agent-session-event.schema.json`
- Описывает события attendance/ledger (`agent.checked_in`, `agent.heartbeat`, …), отдельный слой, не то же самое, что процессные события.
- Эти события пишутся в `runtime/agent-ledger/sessions.ndjson`, а не в `runtime/events/events.ndjson` (хотя часть `agent.*` поступает в runtime через `codex_hooks` и проходит через `append_process_event` после нормализации).

### 6) `schemas/session-telemetry-event.schema.json`
- Отдельный формат private-telemetry (`.pf/runtime/telemetry/<session>.ndjson`), не conflates с `event_envelope`.
- Валидация/наблюдение: отдельный канал, отличается от hook/event pipeline.

## Ключевые расхождения и примечания к совместимости

1. **Несовпадение enum событий**
   `schemas/process-event.schema.json` не содержит многих реально используемых типов из `REQUIRED_PROCESSFORGE_EVENT_TYPES`, поэтому является неканоничной для runtime-нагрузки. Для проверки событий используетcя валидация envelope и runtime-пути не опираются на этот enum в целом.

2. **Реестр и фактическая схема событий неравнозначны**
   `event-envelope` требует больше обязательных полей, чем `process-event`, но валидация `validate_event_object` проверяет ещё и меньше (только базовый набор + паттерн `event_type`), поэтому потенциально может пропускать частичные расхождения с `process-event` без hard-fail на уровне CLI.

3. **Разделение `chat.message.recorded` и `session.message.recorded`**
   - `chat.message.recorded`: 1:1 с каждой записью в transcript.
   - `session.message.recorded`: агрегатный маркер экспорта (например, `chat-export`), не замена реального transcript event.

4. **Codex-hook слой не передаёт диалог как чат-содержимое**
   `tools/pf_runtime/codex_hooks.py` трансформирует только `SessionStart/SessionEnd/PostToolUse`, без захвата assistant/user message body; это отдельный слой наблюдения по сессии и инструментам.
