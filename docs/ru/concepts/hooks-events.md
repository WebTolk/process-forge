# Hooks и события

ProcessForge разделяет native agent observations, ProcessForge events и
project-visible chat records.

```text
native agent hook/event
  -> provider adapter
  -> project private raw ingress
  -> normalization and project-scope validation
  -> project event, conversation record, Ledger effect, or no derived effect
```

## Terms and storage boundary

- **Сырое событие** — исходные данные провайдера. Его квитанция и необязательная
  копия данных хранятся в `.pf/runtime/agent-events/hooks.sqlite3` проекта.
- **Normalized PF event** — provider-neutral derived fact.
- **Project event** — private project record в `.pf/runtime/events/events.sqlite3`;
  это не полный hook journal.
- **Chat message** — private transcript record. Сопутствующий
  `chat.message.recorded` event по умолчанию содержит только metadata.
- **Delivery attempt** — outbox work. **Operator log** — отдельный process
  artifact, а не замена event.

SQLite хранит уникальные квитанции, данные незавершённой обработки, карантин и
необязательную историю. Контрольные точки повторной обработки также относятся
к проекту. Эти данные приватны и исключены из архива поставки. Параметры
`logging.raw_hooks` и `logging.events` наследуются от глобального PFConfig с
проектными переопределениями. См. [описание миграции](hook-journal-sqlite.md).

## Codex adapter and registration

Адаптер Codex распознаёт события сессии, сжатия контекста и вызовов инструментов.
При включённом сборе и действующей привязке `UserPromptSubmit` может записать
сообщение пользователя. `Stop`, `SessionEnd` и `SubagentStop` могут записать
переданное итоговое сообщение. Хранение исходных данных регулирует
`logging.raw_hooks`. Полнота стенограммы зависит от полей, которые доставил хост.

Если режим workplace по умолчанию — `organized`, инициализация проекта готовит
восемь обработчиков в `.codex/hooks.json`. В Garage оператор может добавить их
через `tools/pf_runtime/codex_integration.py`. Активацию показывает `/hooks`
в конкретном клиенте Codex. [Настройка хуков](../guides/forge-init-hooks.md) ·
[Чтение данных сессии](../../concepts/codex-session-read.md)

## Project hooks

Диспетчер выбирает включённые цели из `.pf/hooks.yaml` по типу события или
маске `*`. Сухой прогон перечисляет совпадения. В режиме outbox цель типа
`webhook` может создать локальный файл. Для `command` записывается результат
`skipped`. [Маршрутизация событий](../../concepts/hooks-and-webhooks.md)

```bash
python .pf/runtime/bin/pf.py hooks-dispatch --project-root . --event-type assignment.completed --dry-run
```

File-first runtime не требует daemon или network delivery. Optional PF Runtime
service startup и Windows autostart отделены от project outbox routing.
