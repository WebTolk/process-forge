# Live-проверка: Codex events → ProcessForge → MCP

Дата: 2026-08-22

## Итог

**FAIL для полного захвата сообщений, PASS для raw ingress, Ledger и MCP
маршрутизации.**

Свежий одноразовый Codex-сеанс с доверенными project-local hooks выполнил
маркерный запрос и вернул ожидаемый final ответ. ProcessForge получил реальные
события от adapter `codex-hooks`.

## Подтверждённые факты

- В private raw journal присутствуют ровно три события этой сессии:
  `SessionStart`, `UserPromptSubmit`, `SessionEnd`.
- Ledger зарегистрировал сессию и затем корректно закрыл её.
- Установленный beta.2 MCP вернул эту же identity из `pf.session_context` и
  lifecycle факты из `pf.session_activity`.
- `events-validate` завершился PASS.
- `pf.session_chat` вернул **0** сообщений. Реальный пользовательский prompt
  сохранён только в private raw journal, а project transcript не пополнился.
- Native `Stop` не пришёл в этом режиме `codex exec`; поэтому assistant final
  не был доступен adapter'у как `last_assistant_message` и не мог быть записан
  в transcript.

## Причина первого сбоя

Наблюдательные handlers для `SessionStart` и `UserPromptSubmit` помечены
асинхронными. Host сохраняет raw receipt, но для derived conversation message
немедленно требует существующий Ledger presence. Raw receipt `SessionStart`
не является барьером завершения его derived регистрации: соседний
`UserPromptSubmit` может проверяться до создания presence. Поэтому его
conversation effect отклоняется как неавторизованный, хотя raw ingress
сохраняется и subsequent MCP session read работает.

## Граница проверки

Это доказательство свежего реального Codex host, а не только synthetic smoke.
Оно не утверждает, что `Stop` должен быть доступен в `codex exec`: для этого
режима он фактически не был передан host'ом. Необходима отдельная remediation
задача: выбрать и проверить ordering/буферизацию `SessionStart` относительно
message capture, а также зафиксировать поддержку final assistant capture по
режимам Codex.
