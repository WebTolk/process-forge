# Kimi: уточнение поколения клиента

2026-10-22. Дополнение к запечатанному `source-map.md`, а не его изменение.

Локальный launcher ссылается на npm-пакет `@moonshot-ai/kimi-code`; package.json установленной поставки сообщает **2.3.0**. Это новое TypeScript-поколение, не Python `kimi-cli`. Приватные настройки, credentials и содержимое сессий не читались. Проверены только package metadata и ограниченные фрагменты установленного программного bundle. Клиент/модель не запускались.

В установленном bundle подтверждены `usage.record`, поля `agentId`, `model`, `usage`, необязательный `usageScope`, а также суммирование записанного usage в `UsageAgentModel`. Токены представлены `inputOther`, `inputCacheRead`, `inputCacheCreation`, `output`. Вход — сумма трёх входных категорий. Это проверка программной схемы, ещё не реального receipt, сохранности при сбое или полноты собираемого usage.

Первичные источники, просмотрены 2026-10-22:

- [UsageRecord](https://github.com/MoonshotAI/kimi-code/blob/main/packages/agent-core-v2/src/agent/usage/usageOps.ts): durable `usage.record`, scope `session | turn`.
- [UsageAgentModel](https://github.com/MoonshotAI/kimi-code/blob/main/packages/agent-core-v2/src/session/usage/usageAgentModel.ts): запись содержит переданное usage; накопительное состояние получается прибавлением; scope выбирается по типу source. **`usageScope=session` не доказывает, что запись — накопительный снимок.** Нельзя отбрасывать такие записи общим правилом.
- [TokenUsage](https://github.com/MoonshotAI/kimi-code/blob/main/packages/agent-core-v2/src/human/llm/usage.ts): отдельные входные компоненты, output, функции inputTotal/grandTotal.
- [Wire manifest](https://github.com/MoonshotAI/kimi-code/blob/main/packages/agent-core-v2/docs/wire-manifest.d.ts): durable записи лежат в `wire.jsonl`, имеют metadata protocol_version; `usage.record` и `turn.ended` — разные факты. Повторные summary/status и родительское зеркало subagent не должны прибавляться к первичным расходам.
- [External hooks](https://github.com/MoonshotAI/kimi-code/blob/main/packages/agent-core-v2/src/features/externalHooks/agent/agentExternalHooksService.ts), сопоставлены с установленным bundle: PreCompact передаёт context token count. Поле не становится фактическим расходом из-за наличия слова token.

Два разных адаптера/профиля совместимости: современный `kimi-code` usage.record и, только если нужен, прежний `kimi-cli` StatusUpdate.token_usage. Смысл scope/delta/snapshot задаёт проверенная версия источника; название поля и сторонний dashboard не являются контрактом PF.

Рекомендация для первой реализации: начинать Kimi-коллектор с установленного современного формата, получать уже записанные факты из точно выбранной/разрешённой сессии или поддерживаемого потока. Проверить идентичность каждой записи, поведение fork/export/rotation/replay, compaction, retries и child agents. Не сканировать домашние каталоги всех агентов. Session-scope расход с доказанным проектом, но без Work binding, остаётся проектным непривязанным расходом. Привязка к задаче только по проверенному интервалу/turn/native identity, не к последней открытой карточке.
