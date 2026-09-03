# Оценка готовности: централизованный `chat-capture` без новой сущности

## 1) Может ли существующая модель принимать автоматический provider-контент?

Да, **с текущей моделью чата/событий можно захватывать провайдерные сообщения без новой сущности**, но с оговорками по провайдерам:
- `chat-record` уже пишет в transcript (`.pf/runtime/chat/transcripts/<session-id>.ndjson`) объект по `schemas/chat-message.schema.json`.
- Сразу после записи той же записи публикуется событие `chat.message.recorded`.
- Минимальный жизненный цикл уже присутствует: `record` (строка transcript) + `chat.message.recorded` (событие) на каждый message.

## 2) Точный набор полей (что уже есть)

### 2.1. Transcript record (`chat-message.schema.json`)
Обязательные:
- `schema_version`
- `message_id`
- `session_id`
- `turn_id`
- `timestamp`
- `participant`:
  - `id`
  - `type` (`human|agent|subagent|tool`)
  - `role`
- `message`:
  - `role` (`user|assistant|system|tool|subagent`)
  - `content_type`
  - `content`
  - `content_hash` (`sha256:<hex64>`)
  - `redaction`
- `source`
- (в реализации также присутствуют): `process`, `assignment`, `parent_message_id`
- в `source` уже реально используется `kind`, плюс служебные поля (`hook_event`, `transcript_path`) через `additionalProperties`.

### 2.2. `chat.message.recorded` payload (`event.data`)
Сейчас формируется с ключами:
- `session_id`
- `message_id`
- `participant`
- `message`:
  - `role`
  - `content_hash`
  - `redaction`
  - `content_ref` (`path`, `line`, `message_id`)
  - `content_mode`:
    - `metadata_only` по умолчанию
    - `full` / `redacted` / `truncated` / `redacted_truncated` только при включённой передаче контента

### 2.3. Envelope события (`event-envelope.schema.json`)
Для события нужно соблюдать также обязательные поля envelope:
- `schema_version`, `event_id`, `event_type`, `source`, `subject`, `time`,
  `correlation_id`, `project`, `process`, `assignment`, `actor`, `data`.

## 3) Дублируемость идентичности (duplicate identity)
- **Единая идентичность message-level уже есть**: `message_id` генерируется один раз в `append_chat_message` и используется сразу в transcript и `chat.message.recorded`.
- Корреляция по сессии: `correlation_id = session_id`.
- Для события существует отдельная идентичность `event_id` (строки событий дедуплицируются по `event_id`, а не по `message_id`).

## 4) Наименьший безопасный срез для автозахвата (без новой сущности)
Рекомендуемый минимальный slice для подключения провайдера:
- Заполнять transcript только через существующее `append_chat_message` API:
  - `session_id`, `participant_id`, `participant_role`, `message_role`, `content`, `turn_id`, `source_kind`, `process_id`, `stage_id`, `assignment_id_value`.
- Обязательный `source.kind` для разграничения провайдеров (например `codex_hook` / `claude_hook` / `gemini_hook`) в пределах `source` — уже поддерживается как расширяемое поле.
- Не включать сырое содержимое в событие по умолчанию (`content_mode=metadata_only`, только `content_hash` + `content_ref`).
- Для случаев, где нужно содержимое, включать его явно и только через текущий флаг `include_content` (с уже существующими режимами редакции `redaction`).

Это покрывает автоматический приём метаданных и трассировку/идентификацию без создания новой сущности.

## 5) Что подтверждено, а что не подтверждено

### Подтверждено (фактически в PF и в коде/артефактах)
- Протокол «transcript + chat.event» для одного `message_id` уже работает.
- Корреляция/редакции/`content_ref` реализованы.
- `chat-export` работает как отдельная агрегированная метка с `session.message.recorded` (служебно), но это другой тип события.

### Не подтверждено (на уровне источников/контрактов провайдеров)
- Для **Codex** локально подтвержден частичный adapter:
  - из известных событий реализованы `SessionStart`, `SessionEnd`, `PostToolUse`;
  - в этой проверке нет подтверждения захвата полного содержимого диалога как chat-body из Codex hook stream.
- Для **Claude Code** и **Gemini CLI** в разрешённой области подтверждена только формальная доступность provider contracts, но адаптера в PF нет (подтверждается как отсутствие/нереализованность в доступной матрице).
- Следовательно, автоматический provider content ingestion “из коробки” сейчас подтверждён **только по ограниченному Codex-пути и не по полноценным сообщениям чата всех providers**.
