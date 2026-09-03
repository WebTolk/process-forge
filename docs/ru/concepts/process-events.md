# События процесса

События проекта — приватные производные факты в `.pf/runtime/events/events.ndjson`. Они нужны процессам, hooks и review gates, но не являются полным журналом всех событий агента.

Нативный payload сначала попадает в приватный workplace Raw Event Journal: `<workplace>/runtime/agent-events/`. Только после проверки project scope адаптер может создать нормализованное и затем project event. Поэтому сырой event может остаться unsupported, denied, quarantined либо не иметь эффекта в проекте.

`chat.message.recorded` по умолчанию содержит хеш и ссылку на контент, а не полное тело сообщения. Подробности — в [Hooks и события](hooks-events.md).
