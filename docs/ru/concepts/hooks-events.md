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

Каждая пара из события и точного ID адресата получает собственный ключ доставки.
CLI выводит пути к файлу и квитанции. Квитанция содержит ID события, адресата
и SHA-256 опубликованных байтов. При повторной обработке PF использует исходный
файл с его временной меткой. Если запись квитанции прервалась, повторная
обработка события завершает её по тем же байтам. Журнал сохраняет выбранных
адресатов и их маршруты при приёме события. Смена пути или отключение адресата
действуют для следующих событий. Уже принятое событие получает подтверждение
после завершения исходных доставок. Для старой записи очереди, содержащей
только событие, перед первым повтором восстановите прежнюю конфигурацию хуков.
Неудачные доставки остаются в очереди. В поле `dispatch_failures` проекта
команда Runtime tick выводит ID каждого такого события и причину. Runtime
продолжает обрабатывать остальную часть выборки и при следующих вызовах
возвращается к оставшимся событиям порциями ограниченного размера.

Прежние пути сохраняются для обычных доставок, когда исходный файл подтверждает
точного адресата и событие. Если старая версия прервалась до записи квитанции,
PF завершает её по исходному файлу. Если старая квитанция оборвана или уже
принадлежит другому адресату с тем же нормализованным именем, точный адресат
получает собственную квитанцию на исходные байты. Поле `payload_delivery_id`
содержит прежний ID доставки, а `payload_sha256` позволяет проверить файл
по пути `outbox`. Старые файлы WTAICC хранят только
общее имя интеграции. При повторе PF сохраняет такой файл и записывает новую
доставку с идентификатором конкретного адресата.

```bash
python .pf/runtime/bin/pf.py hooks-dispatch --project-root . --event-type assignment.completed --dry-run
```

File-first runtime не требует daemon или network delivery. Optional PF Runtime
service startup и Windows autostart отделены от project outbox routing.
