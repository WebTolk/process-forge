# Интеграция PF shell-worker плана: remediation захвата Codex-сообщений

## Статус

Планирование завершено. Шесть задач текущего run имеют статус `done`; три из
них были выполнены PF shell-workers через `codex-exec` с model
`gpt-5.3-codex-spark`. Product code не изменялся.

## Роли и результаты

| Worker | Режим | Результат |
| --- | --- | --- |
| `codex-capture-ordering-audit-20260822` | assurance | Подтвердил: raw ingress и MCP работают, но conversation capture может проверять Ledger presence до её materialization. |
| `codex-exec-event-contract-audit-20260822` | assurance | Подтвердил регистрацию hooks; в проверенном `codex exec` нет native `Stop`, поэтому final assistant content adapter не получает. |
| `codex-capture-remediation-architecture-20260822` | planning_only | Предложил минимальный план: ordering/fallback, deferred capture, focused smoke и live-host gate. |

## Принятый boundary implementation

Следующая задача должна иметь отдельный `implementation` scope и владеть
только:

- `tools/pf_runtime/host.py` — сохранить raw-first durable ingress и обеспечить
  capture после успешной session registration либо через ограниченную durable
  deferred/replay модель;
- `tools/pf_runtime/codex_hooks.py` — fallback для final assistant только если
  host действительно передаёт `last_assistant_message` на `SessionEnd`;
- `tools/smoke_conversation_completeness.py` — гонка prompt/session-start,
  idempotency и fallback при доступном final message;
- при необходимости точечный MCP smoke, доказывающий `pf.session_chat`.

В текущем фактическом `codex exec` native `Stop` отсутствовал. Поэтому fix не
должен обещать захват assistant final без поля, которое host не передал;
fallback покрывает только реализацию, где `SessionEnd` содержит это поле.

## Gates до закрытия remediation

1. Raw events, Ledger lifecycle и existing session isolation остаются зелёными.
2. Реальный `UserPromptSubmit`, прибывший до готовности Ledger presence, в
итоге появляется в `pf.session_chat` ровно один раз.
3. Дубликаты и cross-project/session mismatch остаются fail-closed.
4. При доступном `last_assistant_message` fallback создаёт ровно одну assistant
chat запись; при его отсутствии отчёт явно фиксирует host limitation.
5. Пройдут focused smokes, `events-validate`, task/run doctors и новая
проверка live host → raw → transcript → MCP.

## Следующее состояние

Implementation не запущена: этому требуется отдельная assignment с review и
строго ограниченным write scope. Этот integration report является входом для
её создания.
