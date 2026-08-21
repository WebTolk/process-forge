# Передача чата

Transcript диалога хранится приватно в `.pf/runtime/chat/transcripts/<session-id>.ndjson`. Событие `chat.message.recorded` и outbox по умолчанию содержат только метаданные, content hash и локальную ссылку, не полный body.

Текущий адаптер Codex автоматически фиксирует только `UserPromptSubmit` при известных project/session. PF-owned summaries входа worker и ожидаемые отчёты worker также требуют проверяемую provenance. Универсальный захват ответов assistant и сообщений subagent пока отсутствует.

Raw provider payload хранится отдельно в private Raw Event Journal workplace; в project event и outbox его полное тело не копируется.
