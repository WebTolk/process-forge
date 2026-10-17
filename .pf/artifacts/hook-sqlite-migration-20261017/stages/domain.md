# Domain model журналов

Дата: 2026-10-17. Основание: просьба пользователя о SQLite/двух уровнях PFConfig и его понимание журнала как истории решений.

## Понятия

- История проекта: необязательная структурированная последовательность сообщений/действий, с agent/session/Work links. Lifecycle transitions — подробные записи той же истории. Текущее envelope событие сохраняет metadata/ref переписки; содержимое и доставка принадлежат chat subsystem.
- Raw hook copy: необязательная private диагностическая копия native payload; не является источником полномочий или состоянием Work.
- Admission receipt: минимальный ID/digest принятого события для повтора и восстановления. Сохраняется независимо от двух флагов; это не скрытая полная история.
- Pending ingress: native record, необходимый до завершения/отказа в обработке. Когда raw recording выключено, удаляется после завершения; незавершённый payload сохраняется для восстановления.
- Verification state: последнее подтверждение проверки по assignment/event type и fingerprint. Это рабочее состояние, а не накапливаемая история; обновляется и при выключенной истории.
- Доставка/обработка: at-least-once с детерминированными ID и идемпотентными sinks. Локальный commit не обещает exactly-once для будущего внешнего API.

## Настройки

`logging.raw_hooks` и `logging.events`: device defaults true для сохранения существующего поведения. В проектном PFConfig overrides каждый параметр — true/false/null. Null или отсутствие наследует device value; false — явное выключение. Отсутствующий проектный файл означает полное наследование. Никаких зависимостей флагов друг от друга.

Выключенный `logging.events` не добавляет новые envelopes в history table, включая stage/task events. Work YAML/intent/evidence, chat transport, минимальные receipts и последнее verification state продолжают работать. Выключенный `logging.raw_hooks` не оставляет завершённые payloads в raw history. Флаги не стирают старую историю задним числом.

Приём имеет один стабильный ID во время POST/retry/fallback. Сохраняется существующая семантика ID адаптеров. Если explicit ID отсутствует, текущий digest-based ID не превращается автоматически в гарантированный provider ID; ограничение документируется. Native stable-ID conflict с другим payload по-прежнему quarantine.

## Изоляция и порядок

Базы лежат в private runtime каталоге проекта; все его участники используют общие tables и различаются полями. Последовательность SQL seq задаёт порядок сохранения. Read cursor — seq, не timestamp и не offset в файле. Разные проекты не смешиваются.

Состояние сырого приёма и его optional history имеет одного SQL owner; проектные normalized admissions/history/verification state — второго. Raw commit происходит до derived effects. Успешный receipt не предоставляет trust; все прежние policy/scope/provenance checks остаются.

## Миграция

Это явная одноразовая операция, не fallback reader в обычной работе. Она сохраняет ID, envelopes, порядок и raw provenance, различает invalid rows и несовместимые повторные ID, не удаляет оригиналы. Повторный импорт безопасен. Незаконченный импорт отмечается и не считается готовым рабочим журналом. Мигратор не останавливает процессы и не переключает установленный Core.

## Что меняется в представлениях

История читается из SQL по cursor/filter. Полный Markdown export/rebuild остаётся явной операцией. Readiness использует indexed последнее состояние и текущие authoritative inputs. Обычный hook не перестраивает history и не обходит все assignments. Обновление служебной проекции допускается отдельно, с проверкой изменившихся inputs, не на каждом наблюдении агента.
