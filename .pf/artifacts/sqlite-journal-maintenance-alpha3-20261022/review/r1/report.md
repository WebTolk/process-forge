# RESULT: независимое review alpha3 maintenance

**CODE: NO-GO. Review: fail.** Два обязательных исправления.

Проверены все 26 файлов из `source-candidate-r2.json`: реализация primary/W1–W4, регистрация Main, тесты и EN/RU документация. SHA256 каждого файла совпал до и после review. SHA256 manifest: `e7fa6c6c4caaac6126a99ad8f3f17eb19d92f83903f09fb860fd74a2df35752c`.

## Обязательные исправления

1. **P2 — replay отклоняет допустимые NFC-эквивалентные raw payload.**  
   Место: `src/processforge_core/maintenance/journals.py:577`.

   Identity-функции нормализуют Unicode в NFC, поэтому payload со строками `"café"` и `"cafe\u0301"` получают одинаковые `raw_event_id`, `native_identity_key` и `raw_payload_hash`. Scanner и дедупликация допускают такие повторные наблюдения. Однако `_verify_raw` сравнивает JSON без NFC-нормализации и выдаёт `migration_record_mismatch`; импорт остаётся незавершённым.

   Изолированная stdlib-проверка действующих identity-функций и replay подтвердила: идентичный payload проходит, NFC-эквивалентный — отклоняется.

   **Исправление:** проверять реальный сохранённый payload через существующие канонические identity/hash-примитивы. Добавить тест импорта обоих представлений с сохранением исходников и одной записью в БД.

2. **P2 — конфликт ID оставляет карантин без манифеста provenance.**  
   Места: `src/processforge_core/maintenance/journal_scan.py:540`, `src/processforge_core/maintenance/journal_scan.py:480`.

   Триггер: повреждённая строка, затем две корректные строки с одинаковым ID и разным содержимым. Повреждённые байты уже записаны в `.bin`, но `_identity` выбрасывает исключение до `quarantine.finish`. Манифест с source/line/offset/length/hash/reason отсутствует; отчёт сохраняет `quarantine.status: not_requested`.

   Проверка настоящего scanner с SQLite `:memory:` и файловыми операциями в памяти воспроизвела результат: один `.bin`, отсутствие manifest и `migration_event_id_conflict`.

   **Исправление:** сохранять provenance уже помещённых в карантин строк при досрочном отказе, явно отмечая неполное сканирование. Конфликт должен оставаться ошибкой. Добавить проверки «повреждение → конфликт ID» и «повреждение → source drift».

## Проверки и ограничения

Хеши 13 frozen review inputs, восьми QA receipts и их stdout/stderr совпали. Evidence подтверждает записанные результаты: 136 component-тестов, 514 regression-тестов, отдельный junction-тест и exit 0 для lint/format/mypy/Bandit. Проверки reviewer выполнялись стандартной библиотекой; файлы не изменялись.

Тесты содержательно покрывают WAL, concurrent backup, rollback, retry, точные повреждённые байты и подмену записей, но оба найденных сценария отсутствуют.

Независимые snapshots и отдельные commits финализации двух БД — документированное ограничение. Глобальная атомарность не подтверждается и не требуется этим review.

## Незакрытые gates

- Исправления обоих дефектов, regression-тесты, повторный QA и независимое review нового manifest.
- Квалификация чистого committed alpha3: release/schema/cleanliness/checksum/public suite, архив и consumer installation.
- Приёмка на устройстве и connected-host проверка остаются отдельными этапами.

Родительская Work и релиз этим отчётом не закрываются.