# Аудит replay-разрыва: контракт vs `raw_ingress_kernel.py` + `host.py`

Сверка `idempotency-and-replay-contract.md` с текущей реализацией показала следующие **конкретные пробелы для replay**:

## 1) Нет полного replay-движка в runtime
- В `host.ingest_event()` реализован только один проход `ingest -> optional routing`.
- В `raw_ingress_kernel.py` есть durable raw append и recovery индексов, но **нет планировщика replay**, прохода по журналу и приложения только отсутствующих производных эффектов.
- В контракте (`раздел 6`, checkpoint + выбор диапазонов) ожидается replay как отдельный поток обработки, которого сейчас нет.

## 2) Отсутствует контрактный state для replay/checkpoints
- Ни в `raw_ingress_kernel.py`, ни в `host.py` нет записи/чтения checkpoint-файлов для прогресса replay (по проекту/сессии/провайдеру/диапазонам).
- Нет статусов вроде `pending/unsupported_mapping` на уровне replay-прохода.

## 3) Нет проверки детерминированных idempotency-ключей производных эффектов
- В ядре raw есть dedupe на уровне raw и `native_identity_key`, но для производных нет: `project_event`, `ledger_effect`, `chat_message`.
- В `host.py` повторная доставка может обходиться текущей legacy дедупликацией, но нет универсального replay-слоя, который:
  - заново вычисляет ожидаемые производные,
  - проверяет уже применённые эффекты по ключам,
  - и применяет только отсутствующие.

## 4) Нет детектора конфликтов содержимого производного эффекта
- Контракт предусматривает `derived_id_content_conflict` при расхождении уже сохранённого и ожидаемого содержимого.
- В текущем коде такой проверки для replay-прохода нет; для конфликтов есть только raw/quarantine (`native_id_payload_conflict`, `raw_event_id_hash_collision`) на этапе raw-ingest.

## 5) Неполный контрактный индекс raw-событий для replay-аналитики
- В `raw_ingress_kernel._write_index` хранит:
  - `raw_event_id`
  - `raw_payload_hash`
  - `native_identity_key`
  - `raw_location`
  - `routing_status`
- Контракт требует расширенного отражения identity/метаданных (`identity_hash`, `received_at` и др.) для устойчивого replay-аудита и диагностики.

# Минимальный следующий код-слой (без redesign)

1. **Добавить минимальный replay-компонент в `host.py` (или рядом в `tools/pf_runtime/`)**
   - Команда/функция: replay по фильтрам (`provider/session/project/time/raw_id_range`) из raw-журнала (`raw/v1`) с checkpoint-файлом прогресса.
   - Для каждого `raw_event` пересчитывать ожидаемый derived план и применять только отсутствующие эффекты.

2. **Добавить компактный derived-индекс состояния применённых эффектов**
   - Хранить детерминированные ключи по `raw_event_id` + типу эффекта (`project_event`, `ledger_effect`, `chat_message`) и хэшами ожидаемого контента.
   - На replay проверять ключи и применять только missing; при расхождении контента писать quarantine `derived_id_content_conflict`.

3. **Расширить raw-индекс по контракту**
   - Дополнить запись raw-индекса полями (`identity_hash`, `received_at`, метка версии схемы) с обратной совместимостью чтения старых записей.
