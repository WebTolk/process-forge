# Hooks и события

ProcessForge различает нативное наблюдение агента, нормализованное событие PF и видимую проекту запись чата.

```text
нативный hook/event агента
  -> адаптер провайдера
  -> приватный центральный raw ingress workplace
  -> нормализация и проверка project scope
  -> project event, запись диалога, эффект Ledger либо отсутствие производного эффекта
```

## Термины и хранение

- **Сырое нативное событие** — payload провайдера. Сырой журнал событий (Raw Event Journal) хранится приватно в `<workplace>/runtime/agent-events/`.
- **Нормализованное событие PF** — производный platform-neutral факт.
- **Событие проекта** — приватная запись в `.pf/runtime/events/events.ndjson`, но не полный журнал hook-активности.
- **Сообщение чата** — приватная строка transcript. Событие `chat.message.recorded` по умолчанию содержит только метаданные.

Сырой журнал использует часовые shards, индексы дедупликации, quarantine и checkpoints replay. Он может содержать чувствительные данные и не входит в релизный архив.

## Адаптер Codex и регистрация hooks

`tools/pf_runtime/codex_hooks.py` нормализует `SessionStart`, `SessionEnd` и `PostToolUse`. `UserPromptSubmit` принимается raw-first и записывает пользовательский prompt в приватный transcript только при известных session и project.

Возможность адаптера не доказывает регистрацию всех hooks в окружении. Данный дистрибутив не устанавливает `.codex/hooks.json`; приём raw payload, mapping, capture диалога и фактическая регистрация — разные факты. Неизвестное событие может остаться только в сыром журнале.

Общий захват ответов assistant и сообщений host subagent пока не реализован. Project outbox rules живут в `.pf/hooks.yaml`; это не конфигурация нативных hooks Codex.
